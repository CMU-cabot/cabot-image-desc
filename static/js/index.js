// Create the map with OpenLayers
const initialLocation = INITIAL_LOCATION;
var map = new ol.Map({
    target: 'map',
    layers: [
        new ol.layer.Tile({
            source: new ol.source.OSM() // Use OpenStreetMap tiles
        })
    ],
    view: new ol.View({
        center: ol.proj.fromLonLat([initialLocation.lng ?? 0, initialLocation.lat ?? 0]),
        zoom: initialLocation.zoom ?? 21,
        rotation: initialLocation.rotate ?? 0
    })
});

// Enable map rotation with mouse interaction
map.addInteraction(new ol.interaction.DragRotateAndZoom());

var imageLayer = new ol.layer.Vector({
});
var targetLayer = new ol.layer.Vector({
});
map.addLayer(imageLayer);
map.addLayer(targetLayer);

function getMarkerSrc(fill = "#CCCCCC", stroke = "#666666") {
    var angle = 45;
    var heading = 0;
    var path = 'M 22 22 L 22 22 ';
    var size = Math.min(20, 12 * Math.sqrt(180 / angle));
    for (var i = -angle; i < angle + 10; i += 90) {
        i = Math.min(i, angle);
        var r = i / 180 * Math.PI;
        var x = 22 + Math.sin(r) * size;
        var y = 22 - Math.cos(r) * size;
        path += 'L ' + x + ' ' + y + ' ';
    }
    path += 'L 22 22 z';
    return 'data:image/svg+xml,' + encodeURIComponent('<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xml:space="preserve" width="40px" height="40px">'
        + '<path stroke="' + stroke + '" stroke-width="2" stroke-opacity="0.75" fill="' + fill + '" fill-opacity="0.75" d="' + path + '"/></svg>');
}

// Function to query /locations with lat/lng and plot the data
function loadImagesAt(lat, lng, distance=100) {
    fetch(`/locations?lat=${lat}&lng=${lng}&distance=${distance}`) // Query with distance param of 1000 meters
        .then(response => response.json())
        .then(data => {
            var features = [];
            data.forEach(location => {
                var coords = ol.proj.fromLonLat([location.location.coordinates[0], location.location.coordinates[1]]);
                var locationMarker = new ol.Feature({
                    geometry: new ol.geom.Point(coords),
                });

                var markerStyle = new ol.style.Style({
                    'image' : new ol.style.Icon({
                        'src' : getMarkerSrc(),
                        'rotation' : location.direction * Math.PI / 180.0,
                        'rotateWithView' : true,
                        'anchor' : [ 0.5, 0.5 ],
                        'anchorXUnits' : 'fraction',
                        'anchorYUnits' : 'fraction',
                        'imgSize' : [ 44, 44 ]
                    }),
                    'zIndex' : -1
                });
                locationMarker.setStyle(markerStyle);
                features.push(locationMarker);

                // Store additional location details in the feature
                for (key in location) {
                    locationMarker.set(key, location[key]);
                }
            });
            imageLayer.setSource(new ol.source.Vector({
                features: features
            }));
        })
        .catch(error => console.error('Error fetching locations:', error));
}

function loadImages() {
    const center = ol.proj.toLonLat(map.getView().getCenter());
    console.log(["loadImages", center]);
    loadImagesAt(center[1], center[0]);
}

function loadDescriptionAt(lat, lng, rotation, max_count=10, max_distance=100) {
    fetch(`/description?lat=${lat}&lng=${lng}&rotation=${rotation}&max_count=${max_count}&max_distance=${max_distance}`)
        .then(response => response.json())
        .then(data => {
            console.log(data)
	    var locations = data.locations;
            var features = [];
            locations.forEach(location => {
                var coords = ol.proj.fromLonLat([location.location.coordinates[0], location.location.coordinates[1]]);
                var locationMarker = new ol.Feature({
                    geometry: new ol.geom.Point(coords),
                });

                fill = "#666666"
                stroke = "#000000"
                if (location.relative_direction) {
                    if (Math.abs(location.relative_direction) < Math.PI/4) {
                        fill = "#00CC00";
                        stroke = "#006600"
                    }
                    else if (Math.abs(location.relative_direction) < Math.PI/4*3) {
                        if (location.relative_direction > 0) {
                            fill = "#CC0000";
                            stroke = "#660000"
                        }
                        else {
                            fill = "#0000CC";
                            stroke = "#000066"
                        }
                    }
                }

                var markerStyle = new ol.style.Style({
                    'image' : new ol.style.Icon({
                        'src' : getMarkerSrc(fill, stroke),
                        'rotation' : location.direction * Math.PI / 180.0,
                        'rotateWithView' : true,
                        'anchor' : [ 0.5, 0.5 ],
                        'anchorXUnits' : 'fraction',
                        'anchorYUnits' : 'fraction',
                        'imgSize' : [ 44, 44 ]
                    }),
                    'zIndex' : -1
                });
                locationMarker.setStyle(markerStyle);
                features.push(locationMarker);

                // Store additional location details in the feature
                for (key in location) {
                    locationMarker.set(key, location[key]);
                }
            });
            targetLayer.setSource(new ol.source.Vector({
                features: features
            }));
	    showDescription(data);
        })
        .catch(error => console.error('Error fetching locations:', error));
}

function loadDescription() {
    const center = ol.proj.toLonLat(map.getView().getCenter());
    const rotation = map.getView().getRotation();
    console.log(["loadDescription", center, rotation]);
    loadDescriptionAt(center[1], center[0], rotation);
}

// Load locations when the map is moved
map.on('moveend', loadImages);
loadImages();

var mapDiv = document.getElementById("map");
var marker = document.createElement("div");
marker.setAttribute("id", "marker");
marker.setAttribute("title", "Click to generate description")
marker.addEventListener("mouseenter", function() {
    marker.classList.add("hover")
});
marker.addEventListener("mouseleave", function() {
    marker.classList.remove("hover")
});
marker.addEventListener("click", function() {
    loadDescription();
});
mapDiv.insertBefore(marker, mapDiv.firstChild);

// Popup to display location details
var popup = document.getElementById('popup');

// Handle map click events to display location details
map.on('click', function (event) {
    var feature = map.forEachFeatureAtPixel(event.pixel, function (feat) {
        console.log(feat)
        if (feat.get('relative_coordinates')) {
            return feat
        }
    });
    if (!feature) {
        feature = map.forEachFeatureAtPixel(event.pixel, function (feat) {
            return feat
        });
    }
    if (feature) {
        showFeature(feature);
    }
});

function showDescription(result) {
    const description = result.description;
    const elapsed_time = result.elapsed_time;
    var images = "";
    // sort from left (+pi) to right (-pi)
    var locations = result.locations.sort((a, b) => {
	return b.relative_direction - a.relative_direction;
    });
    locations.forEach(location => {
	images += `<img src="${location.image}" width="150">`
    });
    popup.innerHTML = `
        ${images} <br>
        <strong>Description:</strong> ${description} <br>
        <strong>Elapsed Time:</strong> ${elapsed_time} <br>
    `
}

function showFeature(feature) {
    var id = feature.get('_id')
    var description = feature.get('description');
    var direction = feature.get('direction');
    var linuxtime = feature.get('linuxtime');
    var filename = feature.get('filename')
    var date = new Date(linuxtime * 1000);
    var orientation = feature.get('exif')['Orientation']
    var relative_direction = feature.get('relative_direction')
    var relative_coordinates = feature.get('relative_coordinates')
    var image = feature.get('image');
    var tags = feature.get('tags');
    var tagsHTML = `
        <form id="clearTag">
            <input type="hidden" name="id" value="${id}">
            <input type="submit" value="Clear Tag">
        </form>
    `;
    if (tags) {
        tagsHTML += '<ul class="csv-list">';
        // Loop through each tag and add it to the HTML
        tags.forEach(tag => {
            tagsHTML += `<li>${tag}</li>`;
        });
        tagsHTML += '</ul>';
    }
    tagsHTML += `
        <form id="addTag">
            <input type="text" name="tag" placeholder="Add a new tag" id="tagInput">
            <input type="hidden" name="id" value="${id}">
            <input type="submit" value="Add Tag">
        </form>
    `

    var descriptionHTML = `
        <form id="descriptionEdit">
            <textarea name="description">${description}</textarea>
            <input type="hidden" name="id" value="${id}">
            <input type="submit" value="Update">
        </form>
    `;
    
    // Display the information in the popup
    popup.innerHTML = `
        <img src="${image}" alt="Image" style="max-width: 200px; max-height: 200px; float: left; margin: 0px 10px 10px 0px;">
        <strong>${filename}</strong> ${date} <br>
        <strong>Description:</strong> ${descriptionHTML} <br>
        <strong>Orientation:</strong> ${orientation} <br>
        <strong>Tags:</strong> ${tagsHTML} <br>
        <strong>Direction:</strong> ${direction} <br>
    `
    if (relative_direction) {
        popup.innerHTML += `
            <strong>Relative Direction:</strong> ${(relative_direction/Math.PI*180).toFixed(0)} deg (${relative_direction.toFixed(2)} rad, counter clockwise) <br>
        `
    }
    if (relative_coordinates) {
        popup.innerHTML += `
            <strong>Relative Coordinates:</strong> ${relative_coordinates.x.toFixed(2)}, ${relative_coordinates.y.toFixed(2)} <br>
        `
    }

    document.getElementById("clearTag").addEventListener("submit", async function(event) {
        event.preventDefault(); // Prevent form from reloading the page
        const formData = new FormData(event.target);
        const id = formData.get("id");
        try {
            const response = await fetch("/clear_tag?id=" + id, {
                method: "POST",
                body: formData,
            });
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            console.log(response);
            feature.set("tags", [])
            showFeature(feature)
        } catch (error) {
            console.error("Error:", error);
        }
    });
    document.getElementById("addTag").addEventListener("submit", async function(event) {
        event.preventDefault(); // Prevent form from reloading the page
        const formData = new FormData(event.target);
        const id = formData.get("id");
        const tag = formData.get("tag");
        try {
            const response = await fetch("/add_tag?id=" + id, {
                method: "POST",
                body: formData,
            });
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            console.log(response);
            tags = feature.get("tags")
            if (!tags.includes(tag)) {
                tags.push(tag)
            }
            feature.set("tags", tags)
            showFeature(feature)
        } catch (error) {
            console.error("Error:", error);
        }
    });
    document.getElementById("descriptionEdit").addEventListener("submit", async function(event) {
        event.preventDefault(); // Prevent form from reloading the page
        const formData = new FormData(event.target);
        const id = formData.get("id");
        const description = formData.get("description");
        try {
            const response = await fetch("/update_description?id=" + id, {
                method: "POST",
                body: formData,
            });
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            console.log(response);
        } catch (error) {
            console.error("Error:", error);
        }
    });
    popup.style.display = 'block';
}
