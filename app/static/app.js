(function () {
  'use strict';

  var MONTHS = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
  var MONTHS_GEN = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
  var WEEKDAYS = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'];
  var CITY_NOT_FOUND = 'Город не найден, проверьте название';

  function pad(n) { return n < 10 ? '0' + n : String(n); }
  function iso(y, m, d) { return y + '-' + pad(m + 1) + '-' + pad(d); }
  function parseIso(s) {
    var p = s.split('-');
    return new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
  }
  function plural(n, a, b, c) {
    var m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return a;
    if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return b;
    return c;
  }
  function el(tag, props, children) {
    var node = document.createElement(tag);
    if (props) {
      Object.keys(props).forEach(function (k) {
        if (k === 'text') node.textContent = props[k];
        else if (k === 'class') node.className = props[k];
        else node.setAttribute(k, props[k]);
      });
    }
    (children || []).forEach(function (c) { if (c) node.appendChild(c); });
    return node;
  }
  function $(id) { return document.getElementById(id); }

  function api(method, url, body) {
    var opts = { method: method, headers: {} };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    return fetch(url, opts).then(function (r) {
      if (r.status === 204) return null;
      return r.json().catch(function () { return {}; }).then(function (data) {
        if (!r.ok) {
          var err = new Error((data && data.error) || 'Ошибка запроса');
          err.status = r.status;
          throw err;
        }
        return data;
      });
    });
  }

  var now = new Date();
  var todayIso = iso(now.getFullYear(), now.getMonth(), now.getDate());
  var state = {
    year: now.getFullYear(),
    month: now.getMonth(),
    selected: todayIso,
    tasks: [],
    marks: {},
    editId: null,
    city: null,
    wstatus: 'loading',
    wdays: {},
    pick: null
  };

  /* ---------- Погода ---------- */
  function tempFor(ds) {
    if (state.wstatus !== 'ok') return null;
    if (ds < todayIso || ds.slice(0, 7) !== todayIso.slice(0, 7)) return null;
    return state.wdays[ds] || null;
  }

  function renderWeatherNote() {
    var box = $('weather-note');
    box.textContent = '';
    var s = state.wstatus;
    if (s === 'nocity') {
      box.appendChild(document.createTextNode('Выберите город в '));
      box.appendChild(el('a', { href: '#', 'data-action': 'open-settings', text: 'настройках' }));
      box.appendChild(document.createTextNode(', чтобы увидеть прогноз погоды'));
    } else if (s === 'loading') {
      box.textContent = 'Загружаем прогноз погоды…';
    } else if (s === 'error') {
      box.textContent = 'Прогноз погоды временно недоступен';
    } else if (s === 'ok' && state.city) {
      box.textContent = 'Погода: ' + state.city.name;
    }
  }

  function renderDayWeather() {
    var box = $('day-weather');
    var w = tempFor(state.selected);
    if (!w) {
      box.hidden = true;
      box.textContent = '';
      return;
    }
    box.textContent = 'Погода: ' + w.label + ' °C';
    box.hidden = false;
  }

  function loadWeather() {
    state.wstatus = 'loading';
    state.wdays = {};
    renderWeatherNote();
    renderCalendar();
    renderDayWeather();
    return api('GET', '/api/settings').then(function (s) {
      state.city = s.city || null;
      if (!state.city) {
        state.wstatus = 'nocity';
        return null;
      }
      return api('GET', '/api/weather').then(function (data) {
        state.wdays = data.days || {};
        state.wstatus = 'ok';
      });
    }).catch(function () {
      state.wstatus = 'error';
      state.wdays = {};
    }).then(function () {
      renderWeatherNote();
      renderCalendar();
      renderDayWeather();
    });
  }

  /* ---------- Календарь ---------- */
  function renderCalendar() {
    $('month-title').textContent = MONTHS[state.month] + ' ' + state.year;
    var cal = $('calendar');
    Array.prototype.slice.call(cal.querySelectorAll('.c')).forEach(function (n) { n.remove(); });
    var first = new Date(state.year, state.month, 1);
    var offset = (first.getDay() + 6) % 7;
    var daysInMonth = new Date(state.year, state.month + 1, 0).getDate();
    var

 total = Math.ceil((offset + daysInMonth) / 7) * 7;
    for (var i = 0; i < total; i++) {
      var d = new Date(state.year, state.month, 1 - offset + i);
      var ds = iso(d.getFullYear(), d.getMonth(), d.getDate());
      var other = d.getMonth() !== state.month;
      var w = other ? null : tempFor(ds);
      var cls = 'c';
      if (other) cls += ' g';
      if (ds === todayIso) cls += ' today';
      if (ds === state.selected) cls += ' sel';
      if (w) cls += ' wt';
      if (!other && state.marks[ds]) cls += ' mk';
      var label = d.getDate() + ' ' + MONTHS_GEN[d.getMonth()] + (state.marks[ds] && !other ? ', есть дела' : '') + (w ? ', ' + w.label + ' °C' : '');
      var kids = [];
      if (w) kids.push(el('span', { 'class': 'tp', text: w.label }));
      var b = el('button', { type: 'button', 'class': cls, 'data-date': ds, 'aria-label': label }, [el('span', { 'class': 'dn', text: String(d.getDate()) })].concat(kids));
      if (ds === state.selected) b.setAttribute('aria-pressed', 'true');
      cal.appendChild(b);
    }
  }

  function loadMarks() {
    var m = state.year + '-' + pad(state.month + 1);
    return api('GET', '/api/tasks/days?month=' + m).then(function (days) {
      if (m !== state.year + '-' + pad(state.month + 1)) return;
      state.marks = {};
      days.forEach(function (d) { state.marks[d] = true; });
      renderCalendar();
    }).catch(function () { renderCalendar(); });
  }

  function selectDate(ds) {
    state.selected = ds;
    var d = parseIso(ds);
    var monthChanged = d.getMonth() !== state.month || d.getFullYear() !== state.year;
    state.year = d.getFullYear();
    state.month = d.getMonth();
    renderCalendar();
    renderDayWeather();
    if (monthChanged) { state.marks = {}; loadMarks(); }
    loadTasks();
  }

  function shiftMonth(delta) {
    var d = new Date(state.year, state.month + delta, 1);
    state.year = d.getFullYear();
    state.month = d.getMonth();
    state.marks = {};
    renderCalendar();
    loadMarks();
  }

  /* ---------- Дела ---------- */
  function renderDayHeader() {
    var d = parseIso(state.selected);
    $('day-title').textContent = WEEKDAYS[d.getDay()] + ', ' + d.getDate() + ' ' + MONTHS_GEN[d.getMonth()];
    var n = state.tasks.length;
    var done = state.tasks.filter(function (t) { return t.done; }).length;
    var text = n
      ? n + ' ' + plural(n, 'дело', 'дела', 'дел') + ', выполнено ' + done
      : 'На этот день дел нет';
    if (state.selected === todayIso) text = 'Сегодня · ' + text;
    $('day-sub').textContent = text;
    renderDayWeather();
  }

  function renderTasks() {
    var box = $('task-list');
    box.textContent = '';
    renderDayHeader();
    if (!state.tasks.length) {
      var empty = el('div', { 'class': 'empty' }, [
        el('div', { 'class': 'ic', text: '📝' }),
        el('h2', { text: 'День пока свободен' }),
        el('p', { text: 'Добавьте первое дело на этот день: достаточно названия, время и описание можно не указывать.' }),
        el('button', { type: 'button', 'class': 'btn', 'data-action': 'add', text: '+ Добавить дело' })
      ]);
      box.appendChild(empty);
      return;
    }
    var withTime = state.tasks.filter(function (t) { return t.time; });
    var noTime = state.tasks.filter(function (t) { return !t.time; });
    withTime.forEach(function (t) { box.appendChild(taskRow(t)); });
    if (noTime.length) {
      if (withTime.length) box.appendChild(el('div', { 'class': 'sep', text: 'Без времени' }));
      noTime.forEach(function (t) { box.appendChild(taskRow(t)); });
    }
  }

  function taskRow(t) {
    var cb = el('button', {
      type: 'button',
      'class': 'cb' + (t.done ? ' ok' : ''),
      'data-action': 'toggle',
      'data-id': String(t.id),
      'aria-label': t.done ? 'Вернуть в невыполненные' : 'Отметить выполненным',
      'aria-pressed': t.done ? 'true' : 'false',
      text: t.done ? '✓' : ''
    });
    var tm = el('div', { 'class': 'tm' + (t.time ? '' : ' no'), text: t.time || '—' });
    var tt = el('div', { 'class': 'tt' }, [el('b', { text: t.title })]);
    if (t.description) tt.appendChild(el('small', { text: t.description }));
    var act = el('div', { 'class': 'act' }, [
      el('button', { type: 'button', 'data-action': 'edit', 'data-id': String(t.id), 'aria-label': 'Изменить дело', text: '✎' }),
      el('button', { type: 'button', 'data-action': 'delete', 'data-id': String(t.id), 'aria-label': 'Удалить дело', text: '✕' })
    ]);
    return el('div', { 'class': 'task' + (t.done ? ' done' : ''), 'data-id': String(t.id) }, [cb, tm, tt, act]);
  }

  function findTask(id) {
    for (var i = 0; i < state.tasks.length; i++) {
      if (state.tasks[i].id === id) return state.tasks[i];
    }
    return null;
  }

  function loadTasks() {
    var ds = state.selected;
    return api('GET', '/api/tasks?date=' + ds).then(function (tasks) {
      if (ds !== state.selected) return;
      state.tasks = tasks;
      renderTasks();
    }).catch(function () {
      state.tasks = [];
      renderTasks();
      $('day-sub').textContent = 'Не удалось загрузить дела';
    });
  }

  function toggleTask(id) {
    var t = findTask(id);
    if (!t) return;
    api('PATCH', '/api/tasks/' + id + '/done', { done: !t.done }).then(function () {
      return loadTasks();
    }).catch(function () { loadTasks(); });
  }

  function deleteTask(id) {
    var t = findTask(id);
    if (!t) return;
    if (!window.confirm('Удалить дело «' + t.title + '»?')) return;
    api('DELETE', '/api/tasks/' + id).then(function () {
      closeModal();
      return Promise.all([loadTasks(), loadMarks()]);
    }).catch(function () { loadTasks(); loadMarks(); });
  }

  /* ---------- Форма дела ---------- */
  function showTitleError(show) {
    $('title-error').hidden = !show;
    $('f-title').classList.toggle('err', show);
  }

  function showFormError(msg) {
    var box = $('form-error');
    box.textContent = msg || '';
    box.hidden = !msg;
  }

  function openModal(task) {
    state.editId = task ? task.id : null;
    $('modal-title').textContent = task ? 'Изменить дело' : 'Новое дело';
    $('f-title').value = task ? task.title : '';
    $('f-date').value = task ? task.date : state.selected;
    $('f-time').value = task && task.time ? task.time : '';
    $('f-desc').value = task ? task.description : '';
    $('f-delete').hidden = !task;
    showTitleError(false);
    showFormError('');
    $('modal').hidden = false;
    $('f-title').focus();
  }

  function closeModal() {
    $('modal').hidden = true;
    state.editId = null;
  }

  function submitForm(ev) {
    ev.preventDefault();
    var title = $('f-title').value.trim();
    var date = $('f-date').value;
    showFormError('');
    if (!title) {
      showTitleError(true);
      $('f-title').focus();
      return;
    }
    showTitleError(false);
    if (!date) {
      showFormError('Укажите корректную дату');
      return;
    }
    var payload = {
      title: title,
      date: date,
      time: $('f-time').value || null,
      description: $('f-desc').value
    };
    var req = state.editId === null
      ? api('POST', '/api/tasks', payload)
      : api('PUT', '/api/tasks/' + state.editId, payload);
    req.then(function () {
      closeModal();
      if (date !== state.selected) {
        selectDate(date);
      } else {
        loadTasks();
      }
      loadMarks();
    }).catch(function (err) {
      if (err.message === 'Название дела обязательно') {
        showTitleError(true);
      } else {
        showFormError(err.message);
      }
    });
  }

  /* ---------- Настройки ---------- */
  function showCityError(msg) {
    var box = $('city-error');
    box.textContent = msg || '';
    box.hidden = !msg;
  }

  function cityLabel(c) {
    var parts = [c.name];
    if (c.admin) parts.push(c.admin);
    if (c.country) parts.push(c.country);
    return parts.join(', ');
  }

  function hideCityList() {
    var ul = $('city-list');
    ul.textContent = '';
    ul.hidden = true;
  }

  function showCityList(items) {
    var ul = $('city-list');
    ul.textContent = '';
    items.forEach(function (c, i) {
      var b = el('button', { type: 'button', 'data-index': String(i), text: cityLabel(c) });
      ul.appendChild(el('li', null, [b]));
    });
    ul.hidden = !items.length;
  }

  function openSettings() {
    state.pick = null;
    state.found = [];
    $('f-city').value = state.city ? state.city.name : '';
    showCityError('');
    hideCityList();
    $('settings-modal').hidden = false;
    $('f-city').focus();
  }

  function closeSettings() {
    $('settings-modal').hidden = true;
    hideCityList();
  }

  function searchCities(q) {
    return api('GET', '/api/geocode?q=' + encodeURIComponent(q));
  }

  var searchTimer = null;
  var searchSeq = 0;

  function onCityInput() {
    state.pick = null;
    showCityError('');
    var q = $('f-city').value.trim();
    clearTimeout(searchTimer);
    if (q.length < 2) { hideCityList(); return; }
    var seq = ++searchSeq;
    searchTimer = setTimeout(function () {
      searchCities(q).then(function (items) {
        if (seq !== searchSeq) return;
        state.found = items;
        showCityList(items);
      }).catch(function () {
        if (seq !== searchSeq) return;
        hideCityList();
      });
    }, 300);
  }

  function saveCity(city) {
    return api('PUT', '/api/settings/city', city).then(function (saved) {
      state.city = saved;
      closeSettings();
      return loadWeather();
    });
  }

  function submitSettings(ev) {
    ev.preventDefault();
    showCityError('');
    var q = $('f-city').value.trim();
    if (!q) { showCityError(CITY_NOT_FOUND); return; }
    if (state.pick) {
      saveCity(state.pick).catch(function (err) { showCityError(err.message); });
      return;
    }
    clearTimeout(searchTimer);
    searchSeq++;
    searchCities(q).then(function (items) {
      if (!items.length) {
        hideCityList();
        showCityError(CITY_NOT_FOUND);
        return null;
      }
      state.found = items;
      var exact = items.filter(function (c) { return c.name.toLowerCase() === q.toLowerCase(); });
      if (exact.length === 1 || items.length === 1) {
        return saveCity(exact.length === 1 ? exact[0] : items[0]);
      }
      showCityList(items);
      showCityError('Выберите город из списка');
      return null;
    }).catch(function (err) {
      showCityError(err.message || CITY_NOT_FOUND);
    });
  }

  /* ---------- Новости ---------- */
  function fmtTime(isoStr) {
    if (!isoStr) return '';
    var d = new Date(isoStr);
    if (isNaN(d.getTime())) return '';
    return pad(d.getHours()) + ':' + pad(d.getMinutes());
  }

  function renderNewsError() {
    var box = $('news-box');
    box.textContent = '';
    var retry = el('button', { type: 'button', 'class': 'retry', 'data-action': 'retry-news', text: 'Повторить' });
    box.appendChild(el('div', { 'class': 'alert', role: 'alert' }, [
      el('div', { 'class': 'i', text: '⚠' }),
      el('b', { text: 'Не удалось загрузить новости' }),
      el('p', { text: 'Не удалось получить новости с lenta.ru. Проверьте подключение к интернету и попробуйте ещё раз.' }),
      retry
    ]));
    box.appendChild(el('div', { 'class': 'note', text: 'Календарь и список дел работают как обычно' }));
  }

  function renderNews(items) {
    var box = $('news-box');
    box.textContent = '';
    var ul = el('ul', { 'class': 'news' });
    items.slice(0, 10).forEach(function (n) {
      var a = el('a', { href: n.url, target: '_blank', rel: 'noopener noreferrer', text: n.title });
      ul.appendChild(el('li', null, [el('time', { text: fmtTime(n.published) }), a]));
    });
    box.appendChild(ul);
  }

  function loadNews() {
    $('news-box').innerHTML = '<div class="note">Загрузка новостей…</div>';
    api('GET', '/api/news').then(renderNews).catch(renderNewsError);
  }

  /* ---------- События ---------- */
  function bind() {
    $('prev-month').addEventListener('click', function () { shiftMonth(-1); });
    $('next-month').addEventListener('click', function () { shiftMonth(1); });
    $('go-today').addEventListener('click', function () {
      var n = new Date();
      todayIso = iso(n.getFullYear(), n.getMonth(), n.getDate());
      state.year = n.getFullYear();
      state.month = n.getMonth();
      state.marks = {};
      selectDate(todayIso);
      loadMarks();
    });
    $('calendar').addEventListener('click', function (ev) {
      var t = ev.target.closest('.c');
      if (t && t.getAttribute('data-date')) selectDate(t.getAttribute('data-date'));
    });
    $('add-task').addEventListener('click', function () { openModal(null); });
    $('task-list').addEventListener('click', function (ev) {
      var t = ev.target.closest('[data-action]');
      if (!t) return;
      var action = t.getAttribute('data-action');
      var id = Number(t.getAttribute('data-id'));
      if (action === 'add') openModal(null);
      else if (action === 'toggle') toggleTask(id);
      else if (action === 'edit') { var task = findTask(id); if (task) openModal(task); }
      else if (action === 'delete') deleteTask(id);
    });
    $('news-box').addEventListener('click', function (ev) {
      if (ev.target.closest('[data-action="retry-news"]')) loadNews();
    });
    $('task-form').addEventListener('submit', submitForm);
    $('f-title').addEventListener('input', function () {
      if ($('f-title').value.trim()) showTitleError(false);
    });
    $('modal-close').addEventListener('click', closeModal);
    $('f-cancel').addEventListener('click', closeModal);
    $('f-delete').addEventListener('click', function () {
      if (state.editId !== null) deleteTask(state.editId);
    });
    $('modal').addEventListener('mousedown', function (ev) {
      if (ev.target === $('modal')) closeModal();
    });

    $('open-settings').addEventListener('click', openSettings);
    $('weather-note').addEventListener('click', function (ev) {
      if (ev.target.closest('[data-action="open-settings"]')) {
        ev.preventDefault();
        openSettings();
      }
    });
    $('settings-form').addEventListener('submit', submitSettings);
    $('f-city').addEventListener('input', onCityInput);
    $('city-list').addEventListener('click', function (ev) {
      var b = ev.target.closest('button[data-index]');
      if (!b) return;
      var c = state.found[Number(b.getAttribute('data-index'))];
      if (!c) return;
      state.pick = c;
      $('f-city').value = c.name;
      showCityError('');
      hideCityList();
    });
    $('settings-close').addEventListener('click', closeSettings);
    $('settings-cancel').addEventListener('click', closeSettings);
    $('settings-modal').addEventListener('mousedown', function (ev) {
      if (ev.target === $('settings-modal')) closeSettings();
    });
    document.addEventListener('keydown', function (ev) {
      if (ev.key !== 'Escape') return;
      if (!$('modal').hidden) closeModal();
      if (!$('settings-modal').hidden) closeSettings();
    });
  }

  function init() {
    bind();
    renderCalendar();
    renderTasks();
    loadMarks();
    loadTasks();
    loadNews();
    loadWeather();
  }

  init();
})();
