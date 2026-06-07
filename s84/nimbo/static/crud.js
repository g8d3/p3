(function() {
  const configs = {};

  function config(name, opts) {
    configs[name] = opts;
  }

  async function api(method, path, body) {
    const opts = { method, headers: {} };
    if (body) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(path, opts);
    if (res.status === 204) return null;
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'API error');
    return data;
  }

  function renderForm(fields, data = {}) {
    const form = document.createElement('div');
    fields.forEach(f => {
      if (f.name === 'id' || f.name === 'pid') return;
      const div = document.createElement('div');
      div.className = 'field';
      const label = document.createElement('label');
      label.textContent = f.label || f.name;
      label.htmlFor = `f-${f.name}`;
      div.appendChild(label);
      let el;
      if (f.type === 'bool') {
        el = document.createElement('input');
        el.type = 'checkbox';
        if (data[f.name]) el.checked = true;
      } else if (f.type === 'text' || (data[f.name] && String(data[f.name]).length > 80)) {
        el = document.createElement('textarea');
        el.value = data[f.name] || '';
      } else {
        el = document.createElement('input');
        el.type = f.type === 'int' || f.type === 'float' ? 'number' : 'text';
        if (f.type === 'float') el.step = 'any';
        el.value = data[f.name] !== undefined && data[f.name] !== null ? data[f.name] : '';
      }
      el.id = `f-${f.name}`;
      el.name = f.name;
      div.appendChild(el);
      form.appendChild(div);
    });
    return form;
  }

  function collectForm(form) {
    const data = {};
    form.querySelectorAll('[name]').forEach(el => {
      if (el.type === 'checkbox') data[el.name] = el.checked;
      else if (el.type === 'number') data[el.name] = el.value ? Number(el.value) : null;
      else data[el.name] = el.value;
    });
    return data;
  }

  function showToast(msg, type = '') {
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 2500);
  }

  function modal(content, title = '') {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    const box = document.createElement('div');
    box.className = 'modal';
    if (title) {
      const h2 = document.createElement('h2');
      h2.textContent = title;
      box.appendChild(h2);
    }
    box.appendChild(content);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    return { overlay, box, close: () => overlay.remove() };
  }

  function mount(container, resource, fields) {
    const cfg = configs[resource] || {};
    const idField = cfg.id || 'id';
    const apiBase = cfg.api || '/api/' + resource;
    const customActions = cfg.actions || [];
    const noCreate = cfg.noCreate || false;
    const noEdit = cfg.noEdit || false;
    let items = [];
    let timer = null;
    let tbody = null;
    let headerEl = null;
    let emptyEl = null;
    let firstRender = true;

    async function load() {
      try {
        items = await api('GET', apiBase);
        render();
      } catch (e) {
        showToast('Error: ' + e.message, 'error');
      }
    }

    async function onDelete(item) {
      if (cfg.delete) {
        await cfg.delete(item);
      } else {
        if (!confirm('Delete this item?')) return;
        await api('DELETE', `${apiBase}/${item[idField]}`);
      }
      showToast('Deleted', 'success');
      load();
    }

    function render() {
      const displayFields = fields.filter(f => f.name !== idField);

      if (firstRender) {
        container.innerHTML = '';
        headerEl = document.createElement('div');
        headerEl.className = 'flex items-center justify-between mb';
        container.appendChild(headerEl);

        if (customActions.length > 0 || !noEdit || !cfg.delete) {
          const wrap = document.createElement('div');
          wrap.className = 'table-wrap';
          const table = document.createElement('table');
          const thead = document.createElement('thead');
          const tr = document.createElement('tr');
          displayFields.forEach(f => {
            const th = document.createElement('th');
            th.textContent = f.label || f.name;
            tr.appendChild(th);
          });
          const thActions = document.createElement('th');
          thActions.textContent = '';
          tr.appendChild(thActions);
          thead.appendChild(tr);
          table.appendChild(thead);
          tbody = document.createElement('tbody');
          tbody.id = resource + '-tbody';
          table.appendChild(tbody);
          wrap.appendChild(table);
          container.appendChild(wrap);
        }
        emptyEl = document.createElement('p');
        emptyEl.className = 'text-muted text-center';
        container.appendChild(emptyEl);
        firstRender = false;
      }

      headerEl.innerHTML = '';
      const h3 = document.createElement('h3');
      h3.textContent = resource;
      headerEl.appendChild(h3);
      if (!noCreate) {
        const addBtn = document.createElement('button');
        addBtn.className = 'btn btn-primary btn-sm';
        addBtn.textContent = '+ New';
        addBtn.onclick = () => showForm({});
        headerEl.appendChild(addBtn);
      }

      if (items.length === 0) {
        emptyEl.style.display = '';
        emptyEl.textContent = 'No items.';
        if (tbody) tbody.innerHTML = '';
        return;
      }
      emptyEl.style.display = 'none';

      if (tbody) {
        tbody.innerHTML = '';
        items.forEach(item => {
          const row = document.createElement('tr');
          displayFields.forEach(f => {
            const td = document.createElement('td');
            let val = item[f.name];
            if (f.type === 'bool') {
              td.innerHTML = val ? '<span class="badge badge-green">✓</span>' : '<span class="badge">✗</span>';
            } else if (f.type === 'float') {
              td.textContent = val !== null && val !== undefined ? Number(val).toFixed(1) : '';
            } else {
              td.textContent = val !== null && val !== undefined ? String(val).slice(0, 100) : '';
            }
            row.appendChild(td);
          });
          const tdActions = document.createElement('td');
          tdActions.className = 'btn-group';
          customActions.forEach(a => {
            const btn = document.createElement('button');
            btn.className = `btn btn-sm ${a.class || ''}`;
            btn.textContent = a.label;
            btn.onclick = (e) => a.handler(item, btn, e);
            tdActions.appendChild(btn);
          });
          if (!noEdit && !cfg.delete) {
            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-sm';
            editBtn.textContent = '✎';
            editBtn.onclick = () => showForm(item);
            tdActions.appendChild(editBtn);
            const delBtn = document.createElement('button');
            delBtn.className = 'btn btn-sm btn-danger';
            delBtn.textContent = '✕';
            delBtn.onclick = () => onDelete(item);
            tdActions.appendChild(delBtn);
          }
          row.appendChild(tdActions);
          tbody.appendChild(row);
        });
      }
    }

    function showForm(data) {
      if (cfg.form) {
        cfg.form(data);
        return;
      }
      const isEdit = !!data[idField];
      const form = renderForm(fields, data);
      const actions = document.createElement('div');
      actions.className = 'modal-actions';
      const cancelBtn = document.createElement('button');
      cancelBtn.className = 'btn';
      cancelBtn.textContent = 'Cancel';
      cancelBtn.onclick = () => m.close();
      const saveBtn = document.createElement('button');
      saveBtn.className = 'btn btn-primary';
      saveBtn.textContent = isEdit ? 'Save' : 'Create';
      saveBtn.onclick = async () => {
        const payload = collectForm(form);
        try {
          if (isEdit) {
            await api('PUT', `${apiBase}/${data[idField]}`, payload);
          } else {
            await api('POST', apiBase, payload);
          }
          showToast(isEdit ? 'Saved' : 'Created', 'success');
          m.close();
          load();
        } catch (e) {
          showToast('Error: ' + e.message, 'error');
        }
      };
      actions.appendChild(cancelBtn);
      actions.appendChild(saveBtn);
      form.appendChild(actions);
      const m = modal(form, isEdit ? `Edit ${resource}` : `New ${resource}`);
    }

    load();
    if (cfg.refresh) {
      timer = setInterval(() => {
        load();
        if (window.nimbo && window.nimbo.ws) {
          nimbo.ws.send(JSON.stringify({type:'log',data:{level:'info',content:`${resource} refreshed`,source:'client'}}));
        }
      }, cfg.refresh);
    }
    return () => { if (timer) clearInterval(timer); };
  }

  window.nimbo = window.nimbo || {};
  window.nimbo.crud = { mount, config, api, configs };
})();
