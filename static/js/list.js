
function _loadImages() {
    loadImagesAt(initialLocation.lat, initialLocation.lng, (data, floors) => {
        showList(data);
        showFloorList(floors, data);
    });
}

function showList(data) {
    listDiv.innerHTML = "";
    data.sort((a, b) => {
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
}

function showFloorList(floors, all) {
    floorList = Object.keys(floors).sort();
    floorList.forEach(floor => {
        var floorDiv = document.getElementById(`floor-${floor}`);
        if (floorDiv == null) {
            floorDiv = document.createElement("button");
            floorDiv.setAttribute("id", `floor-${floor}`);
            floorDiv.classList.add("floor");
            floorDiv.innerHTML = `Floor ${floor}`
            floorDiv.addEventListener("click", function () {
                showList(floors[floor]);
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
            showList(all);
        });
        navDiv.appendChild(document.createElement("br"));
        navDiv.appendChild(floorDiv);
    }
}

window.onload = _loadImages;

var listDiv = document.getElementById("list");
var navDiv = document.getElementById("navigation");
