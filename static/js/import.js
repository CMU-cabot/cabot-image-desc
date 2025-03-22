function importFile(fileInput) {
    var formData = new FormData();
    formData.append('file', fileInput.files[0]);
    fileInput.value = '';

    fetch('/import-images', {
        method: 'POST',
        body: formData
    }).then(response => {
        if (response.ok) {
            console.log('File successfully uploaded');
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            console.error('File upload failed');
        }
    }).catch(error => {
        console.error('Error:', error);
    });
}

function deleteImage(id) {
    fetch(id ? `/image/${id}` : '/image', {
        method: 'DELETE'
    }).then(response => {
        if (response.ok) {
            console.log('Image successfully deleted');
            setTimeout(() => {
                location.reload();
            }, id ? 0 : 1000);
        } else {
            console.error('Imagee deletion failed');
        }
    }).catch(error => {
        console.error('Error:', error);
    });
}
