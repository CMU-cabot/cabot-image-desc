// Function to query /locations with lat/lng and plot the data
function loadImagesAt(lat, lng, distance=1000) {
    fetch(`/locations?lat=${lat}&lng=${lng}&distance=${distance}`) // Query with distance param of 1000 meters
        .then(response => response.json())
        .then(data => {
            data.sort( (a, b) => {
                return a.filename.localeCompare(b.filename);
            });
            data.forEach(location => {
                showLocation(location);
            });
        })
        .catch(error => console.error('Error fetching locations:', error));
}

function loadImages() {
    center = [139.77542222222223, 35.62414166666667];
    console.log(["loadImages", center]);
    loadImagesAt(center[1], center[0]);
}

loadImages();

var listDiv = document.getElementById("list");

function showDescription(result) {
    const div = document.createElement("div");
    div.setAttribute("id", result._id);
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
    div.innerHTML = `
        ${images} <br>
        <strong>Description:</strong> ${description} <br>
        <strong>Elapsed Time:</strong> ${elapsed_time} <br>
    `
    listDiv.appendChild(div)
}

function showLocation(location) {
    console.log(location)
    var id = location._id;
    var div = document.getElementById(id);
    if (div == null) {
        div = document.createElement("div");
        div.setAttribute("id", id);
        listDiv.appendChild(div);
    } else {
        div.innerHTML = "";
    }
    div.classList.add("location");
    var description = location.description;
    var direction = location.direction;
    var linuxtime = location.linuxtime;
    var filename = location.filename;
    var date = new Date(linuxtime * 1000);
    var orientation = location.exif.Orientation;
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
    
    // Display the information in the popup
    div.innerHTML = `
        <img src="${image}" alt="Image" style="max-width: 200px; max-height: 200px; float: left; margin: 0px 10px 10px 0px;">
        <strong>${filename}</strong> ${date} <br>
        <strong>Description:</strong> ${descriptionHTML} <br>
        <strong>Orientation:</strong> ${orientation} <br>
        <strong>Tags:</strong> ${tagsHTML} <br>
        <strong>Direction:</strong> ${direction} <br>
    `
    if (relative_direction) {
        div.innerHTML += `
            <strong>Relative Direction:</strong> ${(relative_direction/Math.PI*180).toFixed(0)} deg (${relative_direction.toFixed(2)} rad, counter clockwise) <br>
        `
    }
    if (relative_coordinates) {
        div.innerHTML += `
            <strong>Relative Coordinates:</strong> ${relative_coordinates.x.toFixed(2)}, ${relative_coordinates.y.toFixed(2)} <br>
        `
    }

    document.getElementById(`clearTag-${id}`).addEventListener("submit", async function(event) {
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
            showLocation(location);
        } catch (error) {
            console.error("Error:", error);
        }
    });
    document.getElementById(`addTag-${id}`).addEventListener("submit", async function(event) {
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
            tags = location.tags
            if (!tags.includes(tag)) {
                tags.push(tag)
            }
            location.tags = tags;
            showLocation(location);
        } catch (error) {
            console.error("Error:", error);
        }
    });
    document.getElementById(`descriptionEdit-${id}`).addEventListener("submit", async function(event) {
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
    div.style.display = 'block';

}
