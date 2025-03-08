
// Create the map with OpenLayers
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


function loadDescriptionAt(lat, lng, rotation, max_count = 10, max_distance = 100) {
    fetch(`/description?lat=${lat}&lng=${lng}&floor=${selectedFloor}&rotation=${rotation}&max_count=${max_count}&max_distance=${max_distance}`)
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
                    if (Math.abs(location.relative_direction) < Math.PI / 4) {
                        fill = "#00CC00";
                        stroke = "#006600"
                    }
                    else if (Math.abs(location.relative_direction) < Math.PI / 4 * 3) {
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
                    'image': new ol.style.Icon({
                        'src': getMarkerSrc(fill, stroke),
                        'rotation': location.direction * Math.PI / 180.0,
                        'rotateWithView': true,
                        'anchor': [0.5, 0.5],
                        'anchorXUnits': 'fraction',
                        'anchorYUnits': 'fraction',
                        'imgSize': [44, 44]
                    }),
                    'zIndex': -1
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
            showDescription(data, popup);
        })
        .catch(error => console.error('Error fetching locations:', error));
}

function loadDescription() {
    const center = ol.proj.toLonLat(map.getView().getCenter());
    const rotation = map.getView().getRotation();
    console.log(["loadDescription", center, rotation]);
    loadDescriptionAt(center[1], center[0], rotation);
}

function _loadImages() {
    const center = ol.proj.toLonLat(map.getView().getCenter());
    console.log(["loadImages", center]);

    loadImagesAt(center[1], center[0], (data, floors) => {
        showFloorList(floors);
        showFeatures(data, selectedFloor);
    });
}

var selectedFloor = 0;

function showFeatures(data, floor) {
    var features = [];
    data.forEach(location => {
        if (location.floor != floor && floor != 0) {
            return;
        }
        var coords = ol.proj.fromLonLat([location.location.coordinates[0], location.location.coordinates[1]]);
        var locationMarker = new ol.Feature({
            geometry: new ol.geom.Point(coords),
        });

        var markerStyle = new ol.style.Style({
            'image': new ol.style.Icon({
                'src': getMarkerSrc(),
                'rotation': location.direction * Math.PI / 180.0,
                'rotateWithView': true,
                'anchor': [0.5, 0.5],
                'anchorXUnits': 'fraction',
                'anchorYUnits': 'fraction',
                'imgSize': [44, 44]
            }),
            'zIndex': -1
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
}

function showFloorList(floors) {
    floorList = Object.keys(floors).sort();
    floorList.forEach(floor => {
        var floorDiv = document.getElementById(`floor-${floor}`);
        if (floorDiv == null) {
            floorDiv = document.createElement("button");
            floorDiv.setAttribute("id", `floor-${floor}`);
            floorDiv.classList.add("floor");
            floorDiv.innerHTML = `Floor ${floor}`
            floorDiv.addEventListener("click", function () {
                selectedFloor = floor;
                _loadImages();
            });
            navDiv.appendChild(document.createElement("br"));
            navDiv.appendChild(floorDiv);
        }
    });
    var floorDiv = document.getElementById("floor-all");
    if (floorDiv == null) {
        floorDiv = document.createElement("button");
        floorDiv.setAttribute("id", "floor-all");
        floorDiv.classList.add("floor");
        floorDiv.innerHTML = "Floor All"
        floorDiv.addEventListener("click", function () {
            selectedFloor = 0;
            _loadImages();
        });
        navDiv.appendChild(document.createElement("br"));
        navDiv.appendChild(floorDiv);
    }
}

// Load locations when the map is moved
map.on('moveend', _loadImages);
window.onload = _loadImages;

var mapDiv = document.getElementById("map");
var navDiv = document.getElementById("navigation");
var marker = document.createElement("div");
marker.setAttribute("id", "marker");
marker.setAttribute("title", "Click to generate description")
marker.addEventListener("mouseenter", function () {
    marker.classList.add("hover")
});
marker.addEventListener("mouseleave", function () {
    marker.classList.remove("hover")
});
marker.addEventListener("click", function () {
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

function showFeature(feature) {
    var id = feature.get('_id');
    var location = {
        _id: id,
        description: feature.get('description'),
        direction: feature.get('direction'),
        linuxtime: feature.get('linuxtime'),
        filename: feature.get('filename'),
        exif: {
            Orientation: feature.get('exif')['Orientation'],
            relative_direction: feature.get('relative_direction')
        },
        floor: feature.get('floor'),
        relative_coordinates: feature.get('relative_coordinates'),
        image: feature.get('image'),
        tags: feature.get('tags')
    };
    showLocation(location, popup);
}

function showDescription(result, container) {
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
    container.innerHTML = `
        ${images} <br>
        <strong>Description:</strong> ${description} <br>
        <strong>Elapsed Time:</strong> ${elapsed_time} <br>
    `
}
