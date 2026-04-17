const fetch = globalThis.fetch || require('node-fetch');
const cheerio = require('cheerio');

async function testScrape() {
    console.log("Fetching Bing...")
    let r = await fetch('https://www.bing.com/search?q=proximo+partido+de+atletico+madrid', {
        headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9',
        }
    });
    let text = await r.text();
    let $ = cheerio.load(text);
    $('script, style, noscript').remove();
    console.log("Bing main:", $('#b_results').text().substring(0, 1500).replace(/\s+/g, ' '));
}

testScrape();
