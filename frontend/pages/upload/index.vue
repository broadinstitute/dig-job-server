<template>
  <div class="file-upload">
    <h2>Upload File</h2>
    <FileUpload
        mode="advanced"
        :custom-upload="true"
        @upload="onUpload"
        accept=".gz"
        chooseLabel="Choose File"
        uploadLabel="Upload"
        cancelLabel="Cancel"
        :auto="false">
    </FileUpload>
  </div>
</template>

<script>

export default {
  data() {
    return {
      datasetName: 'example-dataset', // Set datasetName dynamically if needed
    };
  },
  methods: {
    async onUpload(event) {
      const file = event.files[0];

      if (!file) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'No file selected!' });
        return;
      }

      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('/api/upload', {
          method: 'POST',
          headers: {
            'Filename': file.name,
            'DatasetName': this.datasetName, // Use dynamic dataset if needed
            'Authorization': 'Bearer YOUR_ACCESS_TOKEN' // Adjust token fetching mechanism
          },
          body: file
        });

        if (!response.ok) {
          throw new Error('Upload failed');
        }

        const data = await response.json();
        this.$toast.add({ severity: 'success', summary: 'File Uploaded', detail: `File uploaded to ${data.s3_path}` });
      } catch (error) {
        this.$toast.add({ severity: 'error', summary: 'Upload Error', detail: error.message });
      }
    }
  }
};
</script>

<style scoped>
.file-upload {
  max-width: 500px;
  margin: 0 auto;
}
</style>

