// config.js

const CONFIG = {
    MAX_TEXT_LENGTH: 256,
    MIN_TEXT_LENGTH: 30,  
    MIN_WORD_COUNT: 2,
    
    ENDPOINTS: {
        SIMPLIFY: '/simplify',
        VALIDATE: '/validate-text',
        HEALTH: '/health'
    },

};

function getMessages() {
    return {
        INPUT_TOO_SHORT: `Input teks terlalu pendek. Minimal ${CONFIG.MIN_TEXT_LENGTH} karakter.`,
        INPUT_TOO_LONG: `Input terlalu panjang. Maksimal ${CONFIG.MAX_TEXT_LENGTH} karakter.`,
        MIN_WORDS: `Input minimal harus terdiri dari ${CONFIG.MIN_WORD_COUNT} kata.`,
        VALID_INPUT: 'Input valid dan siap disederhanakan.'
    };
}

const MESSAGES = getMessages();