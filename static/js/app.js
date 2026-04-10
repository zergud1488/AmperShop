document.querySelectorAll('.needs-validation').forEach((form) => {
  form.addEventListener('submit', (event) => {
    if (!form.checkValidity()) {
      event.preventDefault();
      event.stopPropagation();
    }
    form.classList.add('was-validated');
  });
});

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/js/sw.js').catch(() => {});
  });
}

const debounce = (fn, wait = 300) => {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
};

const phoneInput = document.getElementById('phoneInput');
const phoneCode = document.getElementById('phoneCountryCode');
const emailInput = document.getElementById('emailInput');
const phoneHint = document.getElementById('phoneValidationHint');
const emailHint = document.getElementById('emailValidationHint');

const validateContact = debounce(async () => {
  if (!phoneInput && !emailInput) return;
  const params = new URLSearchParams({
    phone: phoneInput?.value || '',
    code: phoneCode?.value || '+380',
    email: emailInput?.value || '',
  });
  try {
    const res = await fetch(`/api/validate-contact?${params.toString()}`);
    const data = await res.json();
    if (phoneHint && phoneInput?.value) {
      phoneHint.textContent = data.phone_valid ? `✓ Коректний номер: ${data.phone_normalized}` : 'Номер виглядає некоректним';
      phoneHint.className = `small mt-1 ${data.phone_valid ? 'text-success' : 'text-danger'}`;
    }
    if (emailHint && emailInput?.value) {
      emailHint.textContent = data.email_valid ? '✓ Email виглядає коректно' : 'Email виглядає некоректно';
      emailHint.className = `small mt-1 ${data.email_valid ? 'text-success' : 'text-danger'}`;
    }
  } catch (_) {}
}, 400);

[phoneInput, phoneCode, emailInput].forEach((el) => {
  if (el) el.addEventListener('input', validateContact);
  if (el?.tagName === 'SELECT') el.addEventListener('change', validateContact);
});

function attachAutocomplete(inputId, resultsId, fetcher, onSelect) {
  const input = document.getElementById(inputId);
  const box = document.getElementById(resultsId);
  if (!input || !box) return;

  const search = debounce(async () => {
    const q = input.value.trim();
    if (q.length < 2) {
      box.innerHTML = '';
      box.style.display = 'none';
      return;
    }
    const items = await fetcher(q);
    box.innerHTML = items.map(item => `<button type="button" class="autocomplete-item" data-ref="${item.ref || ''}" data-label="${(item.label || '').replace(/"/g, '&quot;')}">${item.label}</button>`).join('');
    box.style.display = items.length ? 'block' : 'none';
  }, 300);

  input.addEventListener('input', search);
  box.addEventListener('click', (e) => {
    const btn = e.target.closest('.autocomplete-item');
    if (!btn) return;
    onSelect(btn.dataset.label, btn.dataset.ref);
    box.innerHTML = '';
    box.style.display = 'none';
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest(`#${inputId}`) && !e.target.closest(`#${resultsId}`)) {
      box.style.display = 'none';
    }
  });
}

const deliveryMethod = document.getElementById('deliveryMethod');
const cityRefInput = document.getElementById('cityRef');
const citySearch = document.getElementById('citySearch');
const branchSearch = document.getElementById('branchSearch');

const resolveProvider = () => {
  const value = deliveryMethod?.value || '';
  if (value.includes('Нова')) return 'np';
  if (value.includes('Meest')) return 'meest';
  return '';
};

attachAutocomplete('citySearch', 'cityResults', async (q) => {
  const provider = resolveProvider();
  if (!provider) return [];
  const res = await fetch(`/api/shipping/cities?provider=${provider}&q=${encodeURIComponent(q)}`);
  return await res.json();
}, (label, ref) => {
  citySearch.value = label;
  cityRefInput.value = ref;
  if (branchSearch) branchSearch.value = '';
});

attachAutocomplete('branchSearch', 'branchResults', async (q) => {
  const provider = resolveProvider();
  if (!provider) return [];
  const res = await fetch(`/api/shipping/branches?provider=${provider}&city_ref=${encodeURIComponent(cityRefInput?.value || '')}&q=${encodeURIComponent(q)}`);
  return await res.json();
}, (label) => {
  branchSearch.value = label;
});
