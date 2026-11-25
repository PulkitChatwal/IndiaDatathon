/* India Datathon — page behaviour.
   The page is fully readable without this file; everything here is an enhancement. */
(() => {
  'use strict';

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const body = document.body;

  /* ---------- header: shadow once the page has scrolled ---------- */
  const header = $('[data-header]');
  const onScroll = () => header.classList.toggle('is-stuck', window.scrollY > 8);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  /* ---------- mobile menu ---------- */
  const menuButton = $('.menu-toggle');
  const nav = $('#site-nav');
  const setMenu = (open) => {
    menuButton.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('is-open', open);
  };
  menuButton.addEventListener('click', () => setMenu(menuButton.getAttribute('aria-expanded') !== 'true'));
  nav.addEventListener('click', (event) => { if (event.target.closest('a')) setMenu(false); });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menuButton.getAttribute('aria-expanded') === 'true') {
      setMenu(false);
      menuButton.focus();
    }
  });
  document.addEventListener('click', (event) => {
    if (menuButton.getAttribute('aria-expanded') === 'true' && !header.contains(event.target)) setMenu(false);
  });
  window.matchMedia('(min-width: 1101px)').addEventListener('change', (mq) => { if (mq.matches) setMenu(false); });

  /* ---------- highlight the section being read ---------- */
  const navLinks = $$('#site-nav li a[href^="#"]');
  const sections = navLinks.map((a) => document.getElementById(a.getAttribute('href').slice(1))).filter(Boolean);
  if ('IntersectionObserver' in window && sections.length) {
    const visible = new Set();
    const mark = () => {
      const current = sections.find((s) => visible.has(s.id));
      navLinks.forEach((a) => {
        const on = Boolean(current) && a.getAttribute('href') === '#' + current.id;
        a.classList.toggle('is-active', on);
        if (on) a.setAttribute('aria-current', 'location'); else a.removeAttribute('aria-current');
      });
    };
    const spy = new IntersectionObserver((entries) => {
      entries.forEach((entry) => { if (entry.isIntersecting) visible.add(entry.target.id); else visible.delete(entry.target.id); });
      mark();
    }, { rootMargin: '-45% 0px -50% 0px' });
    sections.forEach((s) => spy.observe(s));
  }

  /* ---------- program day tabs ---------- */
  const tabs = $$('.day-tab');
  const panels = $$('[data-day-panel]');
  const selectDay = (index, focus) => {
    tabs.forEach((tab, i) => {
      const on = i === index;
      tab.setAttribute('aria-selected', String(on));
      tab.tabIndex = on ? 0 : -1;
      panels[i].hidden = !on;
    });
    if (focus) tabs[index].focus();
  };
  if (tabs.length) {
    selectDay(0, false);
    tabs.forEach((tab, i) => tab.addEventListener('click', () => selectDay(i, false)));
    $('.day-tabs').addEventListener('keydown', (event) => {
      const current = tabs.findIndex((t) => t.getAttribute('aria-selected') === 'true');
      const last = tabs.length - 1;
      const next = { ArrowRight: current === last ? 0 : current + 1, ArrowLeft: current === 0 ? last : current - 1, Home: 0, End: last }[event.key];
      if (next === undefined) return;
      event.preventDefault();
      selectDay(next, true);
    });
  }

  /* ---------- "show all" for faculty biographies and FAQ answers ---------- */
  $$('[data-expand-all]').forEach((button) => {
    const group = $('[data-group="' + button.dataset.expandAll + '"]');
    const labels = button.dataset.expandAll === 'faq'
      ? ['Show all answers', 'Hide all answers']
      : ['Show all biographies', 'Hide all biographies'];
    const sync = () => {
      const items = $$('details', group);
      const allOpen = items.every((d) => d.open);
      button.setAttribute('aria-pressed', String(allOpen));
      button.textContent = allOpen ? labels[1] : labels[0];
    };
    button.addEventListener('click', () => {
      const items = $$('details', group);
      const open = !items.every((d) => d.open);
      items.forEach((d) => { d.open = open; });
      sync();
    });
    group.addEventListener('toggle', sync, true);
  });

  /* ---------- days to go ---------- */
  const countdown = $('[data-countdown]');
  if (countdown && body.dataset.eventStart) {
    const DAY = 86400000;
    const start = Date.parse(body.dataset.eventStart + 'T00:00:00+05:30');
    const end = Date.parse(body.dataset.eventEnd + 'T23:59:59+05:30');
    const now = Date.now();
    const value = $('[data-countdown-value]', countdown);
    const label = $('[data-countdown-label]', countdown);
    if (now < start) {
      const days = Math.ceil((start - now) / DAY);
      value.textContent = String(days);
      label.textContent = days === 1 ? 'day to go' : 'days to go';
      countdown.hidden = false;
    } else if (now <= end) {
      value.textContent = '';
      label.textContent = 'Happening now';
      countdown.hidden = false;
    }
  }

  /* ---------- helpers for forms ---------- */
  const say = (el, kind, text) => { el.dataset.kind = kind; el.textContent = text; };
  const post = async (form) => {
    const response = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } });
    let data = {};
    try { data = await response.json(); } catch (_) { /* a plain-text reply is fine */ }
    return { ok: response.ok, status: response.status, data };
  };

  /* ---------- email notification signup ---------- */
  const signup = $('[data-signup-form]');
  if (signup) {
    const email = $('#signup-email', signup);
    const consent = $('#signup-consent', signup);
    const result = $('[data-form-result]', signup);
    const button = $('button[type="submit"]', signup);
    const TEXT = {
      invalid: 'Enter a valid email address.',
      consent: 'Please confirm that you want the registration email.',
      pending: 'Check your email and confirm your subscription to receive the registration announcement.',
      confirmed: 'You are on the notification list. We will email you when registration opens.',
      duplicate: 'If this email is already subscribed, you will receive the registration announcement. Check your inbox for any confirmation request.',
      failure: 'We could not save your email. Please try again.',
      demo: 'Preview: the next step would ask you to confirm your email. Nothing has been saved or sent.',
    };
    email.addEventListener('input', () => email.removeAttribute('aria-invalid'));
    signup.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!email.value.trim() || !email.validity.valid) {
        email.setAttribute('aria-invalid', 'true');
        say(result, 'error', TEXT.invalid);
        email.focus();
        return;
      }
      email.removeAttribute('aria-invalid');
      if (!consent.checked) {
        say(result, 'error', TEXT.consent);
        consent.focus();
        return;
      }
      if (body.dataset.signup !== 'live') {
        say(result, 'ok', TEXT.demo);
        signup.reset();
        return;
      }
      button.disabled = true;
      try {
        const reply = await post(signup);
        if (reply.status === 409 || reply.data.status === 'duplicate') say(result, 'ok', TEXT.duplicate);
        else if (reply.ok) { say(result, 'ok', signup.dataset.success === 'confirmed' ? TEXT.confirmed : TEXT.pending); signup.reset(); }
        else say(result, 'error', TEXT.failure);
      } catch (_) {
        say(result, 'error', TEXT.failure);
      } finally {
        button.disabled = false;
      }
    });
  }

  /* ---------- participation form ---------- */
  const pForm = $('[data-participation-form]');
  if (pForm) {
    const result = $('[data-form-result]', pForm);
    pForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (pForm.dataset.participationForm !== 'live') return; // locked: "coming soon"

      $$('.field-error', pForm).forEach((el) => el.remove());
      $$('[aria-invalid]', pForm).forEach((el) => el.removeAttribute('aria-invalid'));
      const problems = [];
      const flag = (field, anchor, message) => {
        const note = document.createElement('span');
        note.className = 'field-error';
        note.textContent = message;
        field.append(note);
        problems.push(anchor);
      };
      $$('input, select, textarea', pForm).forEach((control) => {
        if (control.type === 'checkbox' && control.closest('[data-require-one]')) return;
        if (control.type === 'radio' && $$('input[name="' + control.name + '"]', pForm)[0] !== control) return;
        if (control.checkValidity()) return;
        control.setAttribute('aria-invalid', 'true');
        const field = control.closest('.field');
        const message = control.type === 'email' && control.value ? 'Enter a valid email address.'
          : control.type === 'radio' ? 'Choose one option.'
          : control.type === 'checkbox' ? 'Please tick this box to continue.'
          : 'This field is required.';
        flag(field, control, message);
      });
      $$('[data-require-one]', pForm).forEach((group) => {
        const boxes = $$('input[type="checkbox"]', group);
        if (!boxes.some((b) => b.checked)) flag(group, boxes[0], 'Choose at least one option.');
      });
      if (problems.length) {
        say(result, 'error', problems.length === 1 ? 'Please complete the highlighted field.' : 'Please complete the ' + problems.length + ' highlighted fields.');
        problems[0].focus();
        return;
      }

      const button = $('button[type="submit"]', pForm);
      button.disabled = true;
      say(result, 'ok', 'Sending…');
      try {
        const reply = await post(pForm);
        if (reply.ok) {
          say(result, 'ok', 'Your form has been received. This does not confirm a place. We will email you about next steps.');
          pForm.reset();
        } else {
          say(result, 'error', 'We could not send your form. Please try again.');
        }
      } catch (_) {
        say(result, 'error', 'We could not send your form. Please try again.');
      } finally {
        button.disabled = false;
      }
    });
  }
})();
