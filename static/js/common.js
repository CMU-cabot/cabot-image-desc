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


const initialLocation = INITIAL_LOCATION;
const defaultDistance = initialLocation.distance ?? 100;
// Function to query /locations with lat/lng and plot the data
function loadImagesAt(lat, lng, callback, distance = defaultDistance) {
    fetch(`/locations?lat=${lat}&lng=${lng}&distance=${distance}`) // Query with distance param of 1000 meters
        .then(response => response.json())
        .then(data => {
            // list all floor in location, "unknown" if location.floor is undefined
            var floors = {};
            data.forEach(location => {
                key = location.floor ?? "unknown"
                if (floors[key]) {
                    floors[key].push(location);
                } else {
                    floors[key] = [location];
                }
            });
            callback(data, floors);
        })
        .catch(error => console.error('Error fetching locations:', error));
}

function showLocation(location, div) {
    div.innerHTML = "";
    div.classList.add("location");
    console.log(location);
    var id = location._id;
    var description = location.description;
    var direction = location.direction;
    var linuxtime = location.linuxtime;
    var filename = location.filename;
    var date = new Date(linuxtime * 1000);
    var orientation = location.exif.Orientation;
    const rotateStyle = (Number(orientation) === 3)
      ? "transform: rotate(180deg); transform-origin: center;"
      : "";
    var floor = location.floor;
    var relative_direction = location.exif.relative_direction;
    var relative_coordinates = location.relative_coordinates;
    var image = location.image;
    var tags = location.tags;
    var tagsHTML = `
        <form id="clearTag-${id}">
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
        <form id="addTag-${id}">
            <input type="text" name="tag" placeholder="Add a new tag" id="tagInput">
            <input type="hidden" name="id" value="${id}">
            <input type="submit" value="Add Tag">
        </form>
    `

    var descriptionHTML = `
        <form id="descriptionEdit-${id}">
            <textarea name="description">${description}</textarea>
            <input type="hidden" name="id" value="${id}">
            <input type="submit" value="Update">
        </form>
    `;

    var floorHTML = `
        <form id="floorEdit-${id}">
            <input type="text" name="floor" value="${floor}">
            <input type="hidden" name="id" value="${id}">
            <input type="submit" value="Update">
        </form>
    `;

    // Display the information in the popup
    div.innerHTML = `
        <img src="${image}" alt="Image" style="max-width: 200px; max-height: 200px; float: left; margin: 0px 10px 10px 0px; ${rotateStyle}">
        <button onclick="confirm('Are you sure you want to delete this image?') && deleteImage('${id}')">Delete Image</button>
        <strong>${filename}</strong> ${date} <br>
        <strong>Description:</strong> ${descriptionHTML} <br>
        <strong>Orientation:</strong> ${orientation} <br>
        <strong>Tags:</strong> ${tagsHTML} <br>
        <strong>Floor:</strong> ${floor} ${floorHTML} <strong>Direction:</strong> ${direction} <br>
    `
    if (relative_direction) {
        div.innerHTML += `
            <strong>Relative Direction:</strong> ${(relative_direction / Math.PI * 180).toFixed(0)} deg (${relative_direction.toFixed(2)} rad, counter clockwise) <br>
        `
    }
    if (relative_coordinates) {
        div.innerHTML += `
            <strong>Relative Coordinates:</strong> ${relative_coordinates.x.toFixed(2)}, ${relative_coordinates.y.toFixed(2)} <br>
        `
    }

    document.getElementById(`clearTag-${id}`).addEventListener("submit", async function (event) {
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
            location.tags = [];
            showLocation(location, div);
        } catch (error) {
            console.error("Error:", error);
        }
    });
    document.getElementById(`addTag-${id}`).addEventListener("submit", async function (event) {
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
            tags = location.tags ?? [];
            if (!tags.includes(tag)) {
                tags.push(tag)
            }
            location.tags = tags;
            showLocation(location, div);
        } catch (error) {
            console.error("Error:", error);
        }
    });
    document.getElementById(`descriptionEdit-${id}`).addEventListener("submit", async function (event) {
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
            location.description = description;
            showLocation(location, div);
        } catch (error) {
            console.error("Error:", error);
        }
    });
    document.getElementById(`floorEdit-${id}`).addEventListener("submit", async function (event) {
        event.preventDefault(); // Prevent form from reloading the page
        const formData = new FormData(event.target);
        const id = formData.get("id");
        const floor = formData.get("floor");
        try {
            const response = await fetch("/update_floor?id=" + id, {
                method: "POST",
                body: formData,
            });
            if (!response.ok) {
                throw new Error("Network response was not ok");
            }
            console.log(response);
            location.floor = floor;
            showLocation(location, div);
        } catch (error) {
            console.error("Error:", error);
        }
    });
    div.style.display = 'block';
}