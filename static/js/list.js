
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
