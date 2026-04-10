const { GlobalKeyboardListener } = require("node-global-key-listener");

let isKeyPressed = false;

function initHotkeyService(io) {
    const v = new GlobalKeyboardListener();
    console.log("[Hotkey Service] ⌨️ Receptor global iniciado. Tecla maestra: [F8]");

    v.addListener(function (e, down) {
        // e.name es el nombre de la tecla en node-global-key-listener
        if (e.name === "F8") {
            if (e.state === "DOWN" && !isKeyPressed) {
                isKeyPressed = true;
                // Emitir señal de "Comienza a grabar" al frontend
                io.emit("global_hotkey_down");
            } else if (e.state === "UP" && isKeyPressed) {
                isKeyPressed = false;
                // Emitir señal de "Corta la grabación y procesa" al frontend
                io.emit("global_hotkey_up");
            }
        }
    });
}

module.exports = {
    initHotkeyService
};
