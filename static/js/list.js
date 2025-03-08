
function _loadImages() {
    loadImagesAt(initialLocation.lat, initialLocation.lng, (data) => {
        data.sort( (a, b) => {
            return a.filename.localeCompare(b.filename);
        });
        data.forEach(location => {
            var id = location._id;
            var div = document.getElementById(id);
            if (div == null) {
                div = document.createElement("div");
                div.setAttribute("id", id);
                listDiv.appendChild(div);
            }
            showLocation(location, div);
        });
    });
}
window.onload = _loadImages;

var listDiv = document.getElementById("list");

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
