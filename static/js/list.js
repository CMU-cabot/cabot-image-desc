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
