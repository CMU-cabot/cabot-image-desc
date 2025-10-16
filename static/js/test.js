// Copyright (c) 2024  Carnegie Mellon University
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.

var resultDiv = document.getElementById("result");

// Global variable to store EXIF coordinates from the previewed image
window.lastImageCoordinates = {
    lat: null,
    lng: null,
};

// Renamed helper function to collect common request data from preview.
function prepareRequestData(maxDistance, sentenceLength, useLiveImageOnly) {
    const previewImg = document.getElementById("previewImg");
    if (!previewImg || !previewImg.src) {
        alert("Preview image not available. Please select an image to preview.");
        return null;
    }
    const dataURL = previewImg.src;
    const coords = window.lastImageCoordinates || { lat: 0, lng: 0 };
    const languageSelect = document.getElementById("languageSelect");
    const lang = languageSelect ? languageSelect.value : "";
    const floorInput = document.getElementById("floorInput");
    const floor = floorInput ? parseInt(floorInput.value) || 1 : 1;

    const payload = [{
        position: "front",
        image_uri: dataURL
    }];
    const params = new URLSearchParams({
        lat: coords.lat,
        lng: coords.lng,
        floor: floor,
        rotation: "0",
        max_count: "10",
        max_distance: maxDistance,
        length_index: "0",
        distance_to_travel: "100",
        lang: lang,
        sentence_length: sentenceLength,
        use_live_image_only: useLiveImageOnly,
    });

    return { payload, params };
}

// Helper function to perform fetch request and update the result.
function fetchAndDisplayResult(endpoint, params, payload) {
    // Display that the request is in progress
    document.getElementById("result").innerText = "Requesting...";
    fetch(endpoint + "?" + params.toString(), {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        delete data.locations;
        document.getElementById("result").innerText = JSON.stringify(data, null, 2);
    })
    .catch(err => console.error(err));
}

function surround() {
    // Use common request data
    const sentenceLength = document.getElementById("sentenceLengthSelect").value;
    const useLiveImageOnly = document.getElementById("useLiveImageOnlyCheck").checked;
    const reqData = prepareRequestData("15", sentenceLength, useLiveImageOnly);
    if (!reqData) return;
    const { payload, params } = reqData;

    fetchAndDisplayResult("/description_with_live_image", params, payload);
}

function stopReason() {
    // Use common request data
    const reqData = prepareRequestData("100");
    if (!reqData) return;
    const { payload, params } = reqData;

    fetchAndDisplayResult("/stop_reason", params, payload);
}

// Helper function to convert DMS to Decimal Degrees
function convertDMSToDD(degrees, minutes, seconds, direction) {
    var dd = degrees + minutes / 60 + seconds / 3600;
    if (direction === "S" || direction === "W") {
        dd = dd * -1;
    }
    return dd;
}

// New function to preview the image without calling description()
function previewImage() {
    const input = document.getElementById("imageInput");
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];
    const reader = new FileReader();
    reader.onload = function(e) {
        const img = new Image();
        img.onload = function() {

            // Resize and draw the image on a canvas
            let { width, height } = img;
            const maxSize = 512;
            if (width > maxSize || height > maxSize) {
                const ratio = Math.min(maxSize / width, maxSize / height);
                width = width * ratio;
                height = height * ratio;
            }
            const canvas = document.createElement("canvas");
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext("2d");
            if (navigator.userAgent.toLowerCase().indexOf('firefox') > -1) {
                // Firefox: use multi-step reduction
                var oc = document.createElement('canvas'),
                    octx = oc.getContext('2d');
                oc.width = img.width * 0.5;
                oc.height = img.height * 0.5;
                octx.drawImage(img, 0, 0, oc.width, oc.height);
                octx.drawImage(oc, 0, 0, oc.width * 0.5, oc.height * 0.5);
                ctx.drawImage(oc, 0, 0, oc.width * 0.5, oc.height * 0.5,
                              0, 0, canvas.width, canvas.height);
            } else {
                // Chrome and others
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';
                ctx.drawImage(img, 0, 0, width, height);
            }
            
            // Ensure a preview container exists and update preview image
            let previewDiv = document.getElementById("preview");
            if (!previewDiv) {
                previewDiv = document.createElement("div");
                previewDiv.id = "preview";
                document.body.insertBefore(previewDiv, document.getElementById("result"));
            }
            let previewImg = document.getElementById("previewImg");
            if (!previewImg) {
                previewImg = document.createElement("img");
                previewImg.id = "previewImg";
                previewDiv.appendChild(previewImg);
            }
            previewImg.src = canvas.toDataURL("image/jpeg");
            
            // If EXIF available, extract GPS coordinates and store them globally.
            if (window.EXIF) {
                EXIF.getData(img, function() {
                    var latEXIF = EXIF.getTag(this, "GPSLatitude");
                    var latRef = EXIF.getTag(this, "GPSLatitudeRef");
                    var lngEXIF = EXIF.getTag(this, "GPSLongitude");
                    var lngRef = EXIF.getTag(this, "GPSLongitudeRef");
                    if (latEXIF && lngEXIF && latRef && lngRef) {
                        var lat = convertDMSToDD(latEXIF[0], latEXIF[1], latEXIF[2], latRef);
                        var lng = convertDMSToDD(lngEXIF[0], lngEXIF[1], lngEXIF[2], lngRef);
                        console.log("EXIF Coordinates:", lat, lng);
                        document.getElementById("result").innerText += "\nEXIF Coordinates: " + lat + ", " + lng;
                    }
                    window.lastImageCoordinates = { lat: lat, lng: lng};
                });
            } else {
                window.lastImageCoordinates = { lat: 0, lng: 0 };
            }
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

document.getElementById("imageInput").addEventListener("change", previewImage);
