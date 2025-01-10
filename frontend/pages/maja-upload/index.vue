<template>
  <div v-if="uploadProgress > 0" class="overlay">
    <div class="content">
      <ProgressBar :value="uploadProgress" class="progress-bar" :show-value="false" />
      <p class="text-white">Uploading...</p>
    </div>
  </div>
  <div class="grid">
    <div class="col p-8">
      <div class="field">
        <label for="file" class="block text-900 text-l font-medium mb-2">Browse to Local Files and Upload Them Here</label>
        <FileUpload
            id="file"
            @select="sampleFile"
            @clear="resetFile"
            @remove="resetFile"
            :previewWidth="0"
            :show-upload-button="false"
            class="file-upload"/>
      </div>
      <div class="field">
        <Button
            label="Upload"
            class="w-full p-3 text-xl mt-3"
            icon="pi pi-upload"
            :disabled="formIncomplete"
            @click="uploadData" />
      </div>
      <Toast />
    </div>
  </div>
</template>

<script setup>
import {useUserStore} from "~/stores/UserStore";
import axios from 'axios';
import {useToast} from "primevue/usetoast";
const toast = useToast();
const router = useRouter();

const store = useUserStore();
let fileName = null;
const uploadProgress = ref(0);
let file = ref(null);


function resetFile() {
  file.value = null;
  fileName = null;
}

async function sampleFile(e) {
  file.value = e.files[0];
  fileName = e.files[0].name;
}


const formIncomplete = computed(() => {
  return !file.value;
});

onMounted(() => {
  const route = useRoute();
  if (route.query.success) {
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'File uploaded successfully',
      life: 3000
    });
}
});

async function uploadData() {
  const {presigned_url} = await store.getPresignedUrl(fileName, 'maja-uploads');
  const strippedFile = new Blob([file.value], {type: ''});
  try {
    await axios.put(presigned_url, strippedFile, {
      headers: {
        'Content-Type': '',
      },
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
        );
        onProgress(percentCompleted);
      }
    });
    window.location.href = window.location.pathname + '?success=true';
  } catch (error) {
    console.error("File upload failed:", error);
    throw error;
  }
}

function onProgress(percentCompleted) {
  uploadProgress.value = percentCompleted < 100 ? percentCompleted : 0;
}

</script>

<style scoped>
.file-upload {
  max-width: 500px;
  margin: 0 auto;
}

.overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: rgba(0, 0, 0, 0.2);
  z-index: 1000;
}

.content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 2px solid #FFF;
  border-radius: 8px;
  padding: 20px;
  background-color: #333;
}

.progress-bar {
  width: 20rem;
}

.text-white {
  color: white;
}
</style>

