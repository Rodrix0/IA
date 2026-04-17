const fetch = globalThis.fetch || require('node-fetch');

async function getWeather(location) {
    try {
        const res = await fetch(`https://wttr.in/${encodeURIComponent(location)}?format=3`);
        if (!res.ok) return "No se pudo obtener el clima.";
        let text = await res.text();
        text = text.replace(/\+/g, '').trim(); 
        return `El clima en ${text}`;
    } catch(e) {
        return "Error consultando clima.";
    }
}

async function getCryptoPrice(coinName) {
    try {
        const queryLower = coinName.toLowerCase();
        let queryId = 'bitcoin';
        if (queryLower.includes('eth')) queryId = 'ethereum';
        else if (queryLower.includes('doge')) queryId = 'dogecoin';
        else if (queryLower.includes('solana')) queryId = 'solana';

        const res = await fetch(`https://api.coingecko.com/api/v3/simple/price?ids=${queryId}&vs_currencies=usd`);
        const data = await res.json();
        if (data[queryId] && data[queryId].usd) {
            return `El precio actual de ${queryId} es de $${data[queryId].usd} dólares.`;
        }
        return `No pude encontrar la cotización exacta para la moneda solicitada.`;
    } catch(e) {
        return "Error consultando criptomonedas.";
    }
}

async function getDolarBlue() {
    try {
        const res = await fetch('https://dolarapi.com/v1/dolares/blue');
        const data = await res.json();
        return `El Dólar Blue en Argentina está a $${data.compra} para la compra y $${data.venta} para la venta.`;
    } catch(e) {
        return "Error consultando Dólar Blue.";
    }
}

module.exports = {
    getWeather,
    getCryptoPrice,
    getDolarBlue
};
