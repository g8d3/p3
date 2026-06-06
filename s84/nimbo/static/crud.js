(function() {
  async function api(method, path, body) {
    const opts = { method, headers: {} };
    if (body) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const res = await fetch('/api' + path, opts);
    if (res.status === 204) return null;
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'API error');
    return data;
  }

  function renderForm(fields, data = {}) {
    const form = document.createElement('div');
    fields.forEach(f => {
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

  function renderTable(resource, fields, items, onEdit, onDelete) {
    const wrap = document.createElement('div');
    wrap.className = 'table-wrap';
    const table = document.createElement('table');
    const thead = document.createElement('thead');
    const tr = document.createElement('tr');
    const displayFields = fields.filter(f => f.name !== 'id');
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

    const tbody = document.createElement('tbody');
    items.forEach(item => {
      const row = document.createElement('tr');
      displayFields.forEach(f => {
        const td = document.createElement('td');
        let val = item[f.name];
        if (f.type === 'bool') {
          td.innerHTML = val ? '<span class="badge badge-green">✓</span>' : '<span class="badge">✗</span>';
        } else {
          td.textContent = val !== null && val !== undefined ? String(val).slice(0, 100) : '';
        }
        row.appendChild(td);
      });
      const tdActions = document.createElement('td');
      tdActions.className = 'btn-group';
      const editBtn = document.createElement('button');
      editBtn.className = 'btn btn-sm';
      editBtn.textContent = '✎';
      editBtn.onclick = () => onEdit(item);
      const delBtn = document.createElement('button');
      delBtn.className = 'btn btn-sm btn-danger';
      delBtn.textContent = '✕';
      delBtn.onclick = () => onDelete(item);
      tdActions.appendChild(editBtn);
      tdActions.appendChild(delBtn);
      row.appendChild(tdActions);
      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    return wrap;
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
    let items = [];

    async function load() {
      try {
        items = await api('GET', '/' + resource);
        render();
      } catch (e) {
        showToast('Error loading: ' + e.message, 'error');
      }
    }

    function render() {
      container.innerHTML = '';

      const header = document.createElement('div');
      header.className = 'flex items-center justify-between mb';
      const h3 = document.createElement('h3');
      h3.textContent = resource;
      header.appendChild(h3);
      const addBtn = document.createElement('button');
      addBtn.className = 'btn btn-primary btn-sm';
      addBtn.textContent = '+ New';
      addBtn.onclick = () => showForm({});
      header.appendChild(addBtn);
      container.appendChild(header);

      if (items.length === 0) {
        const empty = document.createElement('p');
        empty.className = 'text-muted text-center';
        empty.textContent = 'No items yet. Click "+ New" to create one.';
        container.appendChild(empty);
        return;
      }

      const table = renderTable(resource, fields, items,
        (item) => showForm(item),
        async (item) => {
          if (!confirm('Delete this item?')) return;
          try {
            await api('DELETE', `/${resource}/${item.id}`);
            showToast('Deleted', 'success');
            load();
          } catch (e) {
            showToast('Error: ' + e.message, 'error');
          }
        }
      );
      container.appendChild(table);
    }

    function showForm(data) {
      const isEdit = !!data.id;
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
            await api('PUT', `/${resource}/${data.id}`, payload);
            showToast('Saved', 'success');
          } else {
            await api('POST', '/' + resource, payload);
            showToast('Created', 'success');
          }
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
  }

  window.nimbo = window.nimbo || {};
  window.nimbo.crud = { mount, api };
})();
