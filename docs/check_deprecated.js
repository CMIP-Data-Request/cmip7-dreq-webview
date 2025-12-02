(async function() {
    const scriptTag = document.currentScript;  // the <script> tag itself
    const version = scriptTag.dataset.dreqVersion;
    const latestFile = scriptTag.dataset.dreqLatest;

    try {
        const response = await fetch(latestFile);
        if (!response.ok) throw new Error("Could not load latest version file");
        const latestVersion = (await response.text()).trim();

        if (version !== latestVersion) {
            // Insert the note exactly at the script tag position
            const note = document.createElement('p');
            note.innerHTML = "<strong>Note:</strong> This version of the Data Request is <strong style='color:red;'>deprecated</strong>.";

            // Replace the script tag with the note (or insert before/after)
            scriptTag.insertAdjacentElement('afterend', note);
        }
    } catch (err) {
        console.error("Error checking deprecated version:", err);
    }
})();
