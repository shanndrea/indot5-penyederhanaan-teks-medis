// Global variables untuk data
let medicalExamples = [];


// Debugging flag
const DEBUG = true;

function debugLog(message, data = null) {
    if (DEBUG) {
        if (data) {
            console.log(`[DEBUG] ${message}`, data);
        } else {
            console.log(`[DEBUG] ${message}`);
        }
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    debugLog('DOM Content Loaded');

    // Deklarasikan semua variabel DOM di level yang tepat
    let inputTextarea, simplifyButton, outputBox, inputValidation, diseaseList, diseaseSearch;

    try {
        // Tunggu sedikit untuk memastikan DOM benar-benar siap
        await new Promise(resolve => setTimeout(resolve, 100));

        // Inisialisasi elemen DOM
        initializeDOMElements();

        // Load data terlebih dahulu sebelum setup UI
        await loadDataFiles();

        // Setup UI setelah data loaded
        initializeUI();

        debugLog('Application initialized successfully');

    } catch (error) {
        console.error('Error during initialization:', error);
        debugLog('Initialization failed', error);
    }

    // Fungsi untuk inisialisasi elemen DOM
    function initializeDOMElements() {
        inputTextarea = document.getElementById('input-text');
        simplifyButton = document.getElementById('simplify-button');
        outputBox = document.getElementById('output-text');
        inputValidation = document.getElementById('input-validation');
        diseaseList = document.getElementById('disease-list');
        diseaseSearch = document.getElementById('disease-search');

        debugLog('DOM Elements initialized:', {
            inputTextarea: !!inputTextarea,
            simplifyButton: !!simplifyButton,
            outputBox: !!outputBox,
            inputValidation: !!inputValidation,
            diseaseList: !!diseaseList,
            diseaseSearch: !!diseaseSearch
        });
    }

    // Fungsi untuk initialize seluruh UI
    function initializeUI() {
        // Initialize komponen
        initializeDiseaseList();
        setupEventListeners();

        // Set initial state
        updateButtonState();

        debugLog('UI initialized successfully');
    }

    async function loadDataFiles() {
        try {
            debugLog('Starting to load data files...');

            const examplesResponse = await fetch('/static/data/medical-examples.json');
            if (!examplesResponse.ok) throw new Error(`Failed to load medical examples: ${examplesResponse.status}`);
            const examplesData = await examplesResponse.json();
            medicalExamples = examplesData.diseases || examplesData.medicalExamples || (Array.isArray(examplesData) ? examplesData : []);
            debugLog('Medical examples loaded', { count: medicalExamples.length });

        } catch (error) {
            console.error('Error loading data files:', error);
            loadFallbackData();
        }
    }

    // Fallback data
    function loadFallbackData() {
        debugLog('Loading fallback data...');
        medicalExamples = [{ id: 1, name: "Hipertensi", description: "Tekanan darah tinggi", example: "Pasien dengan hipertensi memerlukan pengobatan rutin.", category: "Penyakit Kardiovaskular" }, { id: 2, name: "Diabetes Mellitus", description: "Gangguan metabolisme gula darah", example: "Pasien dengan diabetes mellitus tipe 2 memerlukan pengaturan diet.", category: "Penyakit Metabolik" }, { id: 3, name: "Kejang Demam", description: "Kejang saat demam tinggi pada anak", example: "Anak dengan kejang demam sederhana biasanya tidak memerlukan pengobatan.", category: "Penyakit Neurologis" }];
        medicalKeywords = ['penyakit', 'sakit', 'gejala', 'diagnosa', 'obat', 'dokter', 'hipertensi', 'diabetes'];
        nonMedicalIndicators = ['halo', 'selamat pagi', 'terima kasih', 'apa kabar', 'siapa namamu'];
        debugLog('Fallback data loaded');
    }

    function initializeDiseaseList() {
        if (!diseaseList) return;
        diseaseList.innerHTML = '';
        if (!medicalExamples || medicalExamples.length === 0) {
            diseaseList.innerHTML = `<div class="disease-item"><div class="disease-content"><div class="disease-name">Data tidak tersedia</div></div></div>`;
            return;
        }
        medicalExamples.forEach((disease, index) => {
            const diseaseItem = createDiseaseItem(disease, index);
            diseaseList.appendChild(diseaseItem);
        });
        debugLog('Disease list initialized');
    }

    function createDiseaseItem(disease, index) {
        const diseaseItem = document.createElement('div');
        diseaseItem.className = 'disease-item';
        const name = disease.name || disease.term || `Penyakit ${index + 1}`;
        const description = disease.description || disease.definition || 'Deskripsi tidak tersedia';
        const example = disease.example || 'Contoh tidak tersedia';
        const category = disease.category || disease.type || 'Kategori tidak tersedia';
        diseaseItem.innerHTML = `<div class="disease-icon">${index + 1}</div><div class="disease-content"><div class="disease-name">${name}</div><div class="disease-description">${description}</div><div class="disease-example">${category}</div></div>`;
        diseaseItem.addEventListener('click', () => {
            document.querySelectorAll('.disease-item').forEach(item => item.classList.remove('active'));
            diseaseItem.classList.add('active');
            if (inputTextarea) {
                inputTextarea.value = example;
                inputTextarea.focus();
                updateButtonState();
            }
        });
        return diseaseItem;
    }

    function setupEventListeners() {
        debugLog('Setting up event listeners...');
        if (!inputTextarea || !simplifyButton) return;
        setupSearchFunctionality();
        setupSimplifyButton();
        setupInputValidation();
        debugLog('Event listeners setup completed');
    }

    function setupSearchFunctionality() {
        if (!diseaseSearch) return;
        diseaseSearch.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase().trim();
            if (searchTerm === '') {
                initializeDiseaseList();
                return;
            }
            const filteredDiseases = medicalExamples.filter(disease => {
                const name = (disease.name || disease.term || '').toLowerCase();
                const description = (disease.description || disease.definition || '').toLowerCase();
                const category = (disease.category || disease.type || '').toLowerCase();
                return name.includes(searchTerm) || description.includes(searchTerm) || category.includes(searchTerm);
            });
            renderFilteredDiseases(filteredDiseases);
        });
    }

    function renderFilteredDiseases(diseases) {
        if (!diseaseList) return;
        diseaseList.innerHTML = '';
        if (diseases.length === 0) {
            diseaseList.innerHTML = `<div class="disease-item"><div class="disease-content"><div class="disease-name">Tidak ditemukan</div><div class="disease-description">Coba gunakan kata kunci lain</div></div></div>`;
            return;
        }
        diseases.forEach((disease, index) => {
            const diseaseItem = createDiseaseItem(disease, index);
            diseaseList.appendChild(diseaseItem);
        });
    }

    function setupSimplifyButton() {
        if (!simplifyButton) return;
        simplifyButton.addEventListener('click', handleSimplify);
        if (inputTextarea) {
            inputTextarea.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    if (!simplifyButton.disabled) {
                        handleSimplify();
                    }
                }
            });
        }
    }

    function setupInputValidation() {
        if (!inputTextarea) return;
        let validationTimeout;
        inputTextarea.addEventListener('input', () => {
            clearTimeout(validationTimeout);
            validationTimeout = setTimeout(updateButtonState, 300);
        });
        updateButtonState();
    }

    // PERBAIKAN & PENAMBAHAN: Fungsi validasi dengan pesan
    function updateButtonState() {
        if (!simplifyButton || !inputTextarea || !inputValidation) return;

        const text = inputTextarea.value;
        const validationResult = validateInputWithMessage(text);

        simplifyButton.disabled = !validationResult.isValid;

        if (validationResult.message) {
            inputValidation.textContent = validationResult.message;
            inputValidation.className = `input-validation ${validationResult.type}`;
        } else {
            inputValidation.textContent = '';
            inputValidation.className = 'input-validation';
        }
    }

    function validateInputWithMessage(text) {
        const trimmedText = text.trim();
        const maxLength = 256;

        if (trimmedText.length === 0) {
            return { isValid: false, message: '', type: '' };
        }

        const wordCount = trimmedText.split(/\s+/).length;
        if (wordCount < 2) {
            return { isValid: false, message: 'Input minimal harus terdiri dari 2 kata.', type: 'error' };
        }

        if (trimmedText.length < 10) {
            return { isValid: false, message: 'Input teks terlalu pendek.', type: 'error' };
        }

        if (text.length > maxLength) {
            return {
                isValid: false,
                message: `Input terlalu panjang. Maksimal ${maxLength} karakter. (${text.length}/${maxLength})`,
                type: 'error'
            };
        }

        return { isValid: true, message: 'Input valid dan siap disederhanakan.', type: 'success' };
    }

    async function handleSimplify() {
        debugLog('=== handleSimplify START ===');
        if (!inputTextarea || !outputBox || !simplifyButton) return;

        const textToSimplify = inputTextarea.value.trim();
        if (!validateInputWithMessage(textToSimplify).isValid) {
            alert('Teks input tidak valid!');
            return;
        }

        setLoadingState(true);
        outputBox.innerHTML = '';

        try {
            const simplifyResponse = await fetch('/simplify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: textToSimplify }),
            });

            const responseData = await simplifyResponse.json();
            debugLog('Simplify response:', responseData);

            // Handle berdasarkan status
            if (responseData.status === 'blocked') {
                // Kondisi 3: Tidak ada yang dikenali - STOP
                outputBox.innerHTML = `
                <div class="warning-message">
                    <div class="content">
                        <strong>Peringatan:</strong>
                        <span>${responseData.message}</span>
                    </div>
                </div>
            `;
                outputBox.className = 'output-display';

            } else if (responseData.status === 'success') {
                let outputHTML = '';

                // 1. "Bungkus" teks hasil dengan div-nya sendiri
                outputHTML += `<div class="simplified-text">${responseData.simplified_text}</div>`;

                // 2. Jika ada mapping, buat HTML-nya (logika ini tetap sama)
                if (responseData.simplification_map && Object.keys(responseData.simplification_map).length > 0) {
                    mappingHTML = `
        <div class="simplification-info">
            <div class="simplification-title">Model berhasil mengenali:</div>
            <div class="simplification-list">
                ${Object.entries(responseData.simplification_map).map(([original, simplified]) => `
                    <div class="simplification-item">
                        <span class="original-term">${original}</span>
                        <span class="arrow">→</span>
                        <span class="simplified-term">${simplified}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
                    // Gabungkan HTML mapping ke hasil akhir
                    outputHTML += mappingHTML;
                }

                // 3. Masukkan semua HTML yang sudah rapi ke outputBox
                outputBox.innerHTML = outputHTML;
                outputBox.className = 'output-display success';
            } else {
                throw new Error(responseData.error || 'Status response tidak dikenali');
            }

        } catch (error) {
            outputBox.innerHTML = `
            <div class="warning-message">
                <div class="content">
                    <strong>Error:</strong>
                    <span>${error.message}</span>
                </div>
            </div>
        `;
            outputBox.className = 'output-display';
        } finally {
            setLoadingState(false);
        }

        debugLog('=== handleSimplify END ===');
    }

    // Fungsi opsional untuk menampilkan notifikasi mapping kecil
    function showMappingNotification(mapping) {
        const mappingCount = Object.keys(mapping).length;
        const notification = document.createElement('div');
        notification.className = 'mapping-notification';
        notification.innerHTML = `
        <small>✅ ${mappingCount} istilah berhasil disederhanakan</small>
    `;

        // Tambahkan setelah output box
        if (outputBox && outputBox.parentNode) {
            outputBox.parentNode.insertBefore(notification, outputBox.nextSibling);

            // Auto hide setelah 5 detik
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 5000);
        }
    }

    function setLoadingState(isLoading) {
        if (!simplifyButton) return;
        const buttonText = simplifyButton.querySelector('.button-text');
        const loadingSpinner = document.getElementById('loading-spinner');
        if (isLoading) {
            simplifyButton.disabled = true;
            if (buttonText) buttonText.textContent = 'Memproses...';
            if (loadingSpinner) loadingSpinner.style.display = 'inline-block';
        } else {
            if (buttonText) buttonText.textContent = 'Sederhanakan';
            if (loadingSpinner) loadingSpinner.style.display = 'none';
            updateButtonState();
        }
    }
});