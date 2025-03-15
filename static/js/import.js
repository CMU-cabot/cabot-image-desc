function importFile(fileInput) {
    var formData = new FormData();
    formData.append('file', fileInput.files[0]);
    fileInput.value='';

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
