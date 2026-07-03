(function () {
  "use strict";

  const state = {
    excelId: null,
    columns: [],
    imagesId: null,
    imageFilenames: [],
    batchId: null,
    items: [],
    folderName: "gorseller",
    stopRequested: false,
    generating: false,
  };

  const $ = (id) => document.getElementById(id);

  const els = {
    settingsToggle: $("settingsToggle"),
    settingsPanel: $("settingsPanel"),
    apiKeyInput: $("apiKeyInput"),
    saveApiKeyBtn: $("saveApiKeyBtn"),

    excelInput: $("excelInput"),
    excelUploadBtn: $("excelUploadBtn"),
    excelResult: $("excelResult"),
    excelPreviewTable: $("excelPreviewTable"),
    keyColumnSelect: $("keyColumnSelect"),

    imagesInput: $("imagesInput"),
    imagesUploadBtn: $("imagesUploadBtn"),
    imagesResult: $("imagesResult"),

    placeholderChips: $("placeholderChips"),
    promptTemplate: $("promptTemplate"),
    folderNameInput: $("folderNameInput"),
    createBatchBtn: $("createBatchBtn"),

    resultsPanel: $("resultsPanel"),
    unmatchedWarning: $("unmatchedWarning"),
    itemsGrid: $("itemsGrid"),
    progressFill: document.querySelector(".progress-fill"),
    progressLabel: $("progressLabel"),
    generateAllBtn: $("generateAllBtn"),
    stopBtn: $("stopBtn"),
    downloadAllBtn: $("downloadAllBtn"),

    toast: $("toast"),
  };

  function showToast(message, type) {
    els.toast.textContent = message;
    els.toast.className = "toast" + (type ? " " + type : "");
    els.toast.classList.remove("hidden");
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => els.toast.classList.add("hidden"), 4200);
  }

  async function api(path, options) {
    const res = await fetch(path, options);
    let data = null;
    try {
      data = await res.json();
    } catch (e) {
      data = null;
    }
    if (!res.ok) {
      const message = (data && data.error) || `İstek başarısız oldu (${res.status})`;
      throw new Error(message);
    }
    return data;
  }

  // ---------- Settings ----------
  els.settingsToggle.addEventListener("click", () => {
    els.settingsPanel.classList.toggle("hidden");
  });

  els.saveApiKeyBtn.addEventListener("click", async () => {
    try {
      const data = await api("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: els.apiKeyInput.value }),
      });
      showToast(data.configured ? "API anahtarı kaydedildi." : "Anahtar temizlendi.", "success");
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // ---------- Step 1: Excel ----------
  els.excelUploadBtn.addEventListener("click", async () => {
    const file = els.excelInput.files[0];
    if (!file) {
      showToast("Lütfen bir excel dosyası seç.", "error");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    els.excelUploadBtn.disabled = true;
    els.excelUploadBtn.textContent = "Yükleniyor...";
    try {
      const data = await api("/api/excel/upload", { method: "POST", body: formData });
      state.excelId = data.excel_id;
      state.columns = data.columns;
      renderExcelPreview(data);
      renderPlaceholderChips(data.columns);
      showToast(`Excel yüklendi: ${data.row_count} satır bulundu.`, "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      els.excelUploadBtn.disabled = false;
      els.excelUploadBtn.textContent = "Excel'i Yükle";
    }
  });

  function renderExcelPreview(data) {
    const table = els.excelPreviewTable;
    table.innerHTML = "";
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    data.columns.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    data.preview.forEach((row) => {
      const tr = document.createElement("tr");
      data.columns.forEach((col) => {
        const td = document.createElement("td");
        td.textContent = row[col] != null ? row[col] : "";
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    els.keyColumnSelect.innerHTML = "";
    data.columns.forEach((col) => {
      const opt = document.createElement("option");
      opt.value = col;
      opt.textContent = col;
      els.keyColumnSelect.appendChild(opt);
    });

    els.excelResult.classList.remove("hidden");
  }

  function renderPlaceholderChips(columns) {
    els.placeholderChips.innerHTML = "";
    columns.forEach((col) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.textContent = `{${col}}`;
      chip.addEventListener("click", () => insertAtCursor(els.promptTemplate, `{${col}}`));
      els.placeholderChips.appendChild(chip);
    });
  }

  function insertAtCursor(textarea, text) {
    const start = textarea.selectionStart || 0;
    const end = textarea.selectionEnd || 0;
    const before = textarea.value.slice(0, start);
    const after = textarea.value.slice(end);
    textarea.value = before + text + after;
    const cursor = start + text.length;
    textarea.focus();
    textarea.setSelectionRange(cursor, cursor);
  }

  // ---------- Step 2: Images ----------
  els.imagesUploadBtn.addEventListener("click", async () => {
    const files = els.imagesInput.files;
    if (!files || !files.length) {
      showToast("Lütfen en az bir görsel seç.", "error");
      return;
    }
    const formData = new FormData();
    Array.from(files).forEach((f) => formData.append("files", f));
    els.imagesUploadBtn.disabled = true;
    els.imagesUploadBtn.textContent = "Yükleniyor...";
    try {
      const data = await api("/api/images/upload", { method: "POST", body: formData });
      state.imagesId = data.images_id;
      state.imageFilenames = data.filenames;
      renderImageChips(data.filenames);
      showToast(`${data.filenames.length} görsel yüklendi.`, "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      els.imagesUploadBtn.disabled = false;
      els.imagesUploadBtn.textContent = "Görselleri Yükle";
    }
  });

  function renderImageChips(filenames) {
    els.imagesResult.innerHTML = "";
    filenames.forEach((name) => {
      const chip = document.createElement("span");
      chip.className = "chip file-chip";
      chip.textContent = name;
      els.imagesResult.appendChild(chip);
    });
    els.imagesResult.classList.remove("hidden");
  }

  // ---------- Step 3: Create batch ----------
  els.createBatchBtn.addEventListener("click", async () => {
    if (!state.excelId) {
      showToast("Önce excel dosyasını yükle.", "error");
      return;
    }
    if (!state.imagesId) {
      showToast("Önce görselleri yükle.", "error");
      return;
    }
    const promptTemplate = els.promptTemplate.value.trim();
    if (!promptTemplate) {
      showToast("Lütfen bir prompt şablonu yaz.", "error");
      return;
    }
    const keyColumn = els.keyColumnSelect.value;
    const folderName = els.folderNameInput.value.trim() || "gorseller";

    els.createBatchBtn.disabled = true;
    els.createBatchBtn.textContent = "Oluşturuluyor...";
    try {
      const data = await api("/api/batch/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          excel_id: state.excelId,
          images_id: state.imagesId,
          key_column: keyColumn,
          prompt_template: promptTemplate,
          folder_name: folderName,
        }),
      });
      state.batchId = data.batch_id;
      state.items = data.items;
      state.folderName = data.folder_name;
      renderUnmatchedWarning(data);
      renderItemsGrid();
      els.resultsPanel.classList.remove("hidden");
      els.resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      const matchedCount = data.items.filter((i) => i.has_reference).length;
      showToast(`Grup oluşturuldu: ${data.items.length} öğe, ${matchedCount} tanesi görselle eşleşti.`, "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      els.createBatchBtn.disabled = false;
      els.createBatchBtn.textContent = "Grubu Oluştur";
    }
  });

  function renderUnmatchedWarning(data) {
    const noImageCount = data.items.filter((i) => !i.has_reference).length;
    const unmatchedImages = data.unmatched_images || [];
    if (noImageCount === 0 && unmatchedImages.length === 0) {
      els.unmatchedWarning.classList.add("hidden");
      return;
    }
    let msg = "";
    if (noImageCount > 0) {
      msg += `${noImageCount} excel satırı için eşleşen görsel bulunamadı (yalnızca prompt ile üretilecek). `;
    }
    if (unmatchedImages.length > 0) {
      msg += `Eşleşmeyen ${unmatchedImages.length} görsel dosyası kullanılmadı: ${unmatchedImages.join(", ")}`;
    }
    els.unmatchedWarning.textContent = msg;
    els.unmatchedWarning.classList.remove("hidden");
  }

  // ---------- Results grid ----------
  function itemCardId(id) {
    return `item-card-${id}`;
  }

  function renderItemsGrid() {
    els.itemsGrid.innerHTML = "";
    state.items.forEach((item) => {
      els.itemsGrid.appendChild(buildItemCard(item));
    });
    updateProgress();
  }

  function buildItemCard(item) {
    const card = document.createElement("div");
    card.className = "item-card";
    card.id = itemCardId(item.id);

    const imageWrap = document.createElement("div");
    imageWrap.className = "item-image-wrap";
    imageWrap.appendChild(buildImageContent(item));
    card.appendChild(imageWrap);

    const body = document.createElement("div");
    body.className = "item-body";

    const name = document.createElement("div");
    name.className = "item-name";
    name.textContent = item.key_value || "(isimsiz)";
    body.appendChild(name);

    body.appendChild(statusBadge(item));

    const prompt = document.createElement("div");
    prompt.className = "item-prompt";
    prompt.title = item.prompt;
    prompt.textContent = item.prompt;
    body.appendChild(prompt);

    if (item.error) {
      const err = document.createElement("div");
      err.className = "item-error";
      err.textContent = item.error;
      body.appendChild(err);
    }

    const actions = document.createElement("div");
    actions.className = "item-actions";
    const genBtn = document.createElement("button");
    genBtn.className = "small-btn";
    genBtn.textContent = item.generated_url ? "🔁 Tekrarla" : "✨ Üret";
    genBtn.addEventListener("click", () => generateItem(item.id));
    actions.appendChild(genBtn);

    if (item.generated_url) {
      const dl = document.createElement("a");
      dl.className = "small-btn";
      dl.textContent = "⬇";
      dl.href = item.generated_url;
      dl.download = `${item.key_value || item.id}.png`;
      actions.appendChild(dl);
    }
    body.appendChild(actions);

    card.appendChild(body);
    return card;
  }

  function buildImageContent(item) {
    if (item.status === "generating") {
      const spinner = document.createElement("div");
      spinner.className = "spinner";
      return spinner;
    }
    if (item.generated_url) {
      const img = document.createElement("img");
      img.src = item.generated_url;
      img.alt = item.key_value || "";
      if (item.reference_url) {
        const wrapper = document.createDocumentFragment();
        wrapper.appendChild(img);
        const ref = document.createElement("img");
        ref.src = item.reference_url;
        ref.className = "reference-thumb";
        ref.alt = "referans";
        wrapper.appendChild(ref);
        return wrapper;
      }
      return img;
    }
    if (item.reference_url) {
      const img = document.createElement("img");
      img.src = item.reference_url;
      img.alt = item.key_value || "";
      img.style.opacity = "0.55";
      return img;
    }
    const placeholder = document.createElement("div");
    placeholder.className = "placeholder";
    placeholder.textContent = "Henüz üretilmedi";
    return placeholder;
  }

  function statusBadge(item) {
    const span = document.createElement("span");
    const map = {
      matched: ["badge-muted", "Bekliyor · görsel eşleşti"],
      no_image: ["badge-warning", "Bekliyor · referans yok"],
      generating: ["badge-warning", "Üretiliyor..."],
      done: ["badge-success", "Tamamlandı"],
      error: ["badge-danger", "Hata"],
    };
    const [cls, label] = map[item.status] || ["badge-muted", item.status];
    span.className = `badge ${cls}`;
    span.textContent = label;
    return span;
  }

  function updateItemInState(updated) {
    const idx = state.items.findIndex((i) => i.id === updated.id);
    if (idx >= 0) state.items[idx] = updated;
  }

  function refreshCard(item) {
    const existing = document.getElementById(itemCardId(item.id));
    const fresh = buildItemCard(item);
    if (existing) existing.replaceWith(fresh);
  }

  function updateProgress() {
    const total = state.items.length;
    const done = state.items.filter((i) => i.status === "done").length;
    const pct = total ? Math.round((done / total) * 100) : 0;
    els.progressFill.style.width = pct + "%";
    els.progressLabel.textContent = `${done} / ${total} tamamlandı`;
  }

  async function generateItem(itemId) {
    const idx = state.items.findIndex((i) => i.id === itemId);
    if (idx === -1) return;
    state.items[idx] = { ...state.items[idx], status: "generating", error: null };
    refreshCard(state.items[idx]);

    try {
      const data = await api(`/api/batch/${state.batchId}/generate/${itemId}`, { method: "POST" });
      updateItemInState(data.item);
      refreshCard(data.item);
      return data.item;
    } catch (err) {
      const idx2 = state.items.findIndex((i) => i.id === itemId);
      const failed = { ...state.items[idx2], status: "error", error: err.message };
      updateItemInState(failed);
      refreshCard(failed);
      throw err;
    } finally {
      updateProgress();
    }
  }

  els.generateAllBtn.addEventListener("click", async () => {
    if (state.generating) return;
    if (!state.items.length) {
      showToast("Önce bir grup oluştur.", "error");
      return;
    }
    state.generating = true;
    state.stopRequested = false;
    els.generateAllBtn.disabled = true;
    els.generateAllBtn.textContent = "Üretiliyor...";
    els.stopBtn.classList.remove("hidden");

    let errorCount = 0;
    for (const item of [...state.items]) {
      if (state.stopRequested) break;
      try {
        await generateItem(item.id);
      } catch (err) {
        errorCount += 1;
      }
    }

    state.generating = false;
    els.generateAllBtn.disabled = false;
    els.generateAllBtn.textContent = "Tümünü Üret";
    els.stopBtn.classList.add("hidden");

    if (state.stopRequested) {
      showToast("Üretim durduruldu.", "");
    } else if (errorCount > 0) {
      showToast(`Tamamlandı, ancak ${errorCount} öğede hata oluştu.`, "error");
    } else {
      showToast("Tüm görseller başarıyla üretildi!", "success");
    }
  });

  els.stopBtn.addEventListener("click", () => {
    state.stopRequested = true;
  });

  els.downloadAllBtn.addEventListener("click", () => {
    if (!state.batchId) {
      showToast("Önce bir grup oluştur.", "error");
      return;
    }
    const doneCount = state.items.filter((i) => i.status === "done").length;
    if (doneCount === 0) {
      showToast("Henüz üretilmiş görsel yok.", "error");
      return;
    }
    window.location.href = `/api/batch/${state.batchId}/download`;
  });

  // ---------- Init ----------
  (async function init() {
    try {
      const data = await api("/api/settings");
      if (!data.configured) {
        els.settingsPanel.classList.remove("hidden");
      }
    } catch (e) {
      // yoksay
    }
  })();
})();
