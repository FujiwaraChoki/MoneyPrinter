<script lang="ts" setup>
/**
 *
 * GenerateScript
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */
const activeTab = ref("script");
const voiceOptions = ref<{ label: string; value: string }[]>([]);
const availableSongs = ref<string[]>([]);
const finalVideo = ref("");
const router = useRouter();

const API_URL = "http://localhost:8080";

const formModel = ref({
  videoSubject: "",
  aiModel: "g4f",
  extraPrompt: "",
});
const { formRef, rules } = useNaiveForm(formModel);

rules.value = {
  videoSubject: {
    required: true,
    trigger: ["input", "blur"],
  },
  aiModel: {
    required: true,
    trigger: ["change", "blur"],
  },
};
const options = [
  {
    label: "FREE",
    value: "g4f",
  },
  {
    label: "GPT 4",
    value: "gpt4",
  },
  {
    label: "GPT 3.5 Turbo",
    value: "gpt3.5-turbo",
  },
];

const isLoading = ref(false);

onMounted(async () => {
  const { data: songsResponse } = await $fetch<{ data: { songs: string[] } }>(
    `${API_URL}/api/getSongs`
  );
  availableSongs.value = songsResponse.songs;
  const { data } = await $fetch<{ data: { voices: string[] } }>(
    `${API_URL}/api/models`
  );
  voiceOptions.value = data.voices.map((voice) => {
    return { label: voice, value: voice };
  });
});
/*----------  Step 2  ----------*/
const videoModel = ref({
  script: "",
  search: "",
  voice: "en_us_001",
});
const { formRef: videoFormRef, rules: videoRules } = useNaiveForm(videoModel);
videoRules.value = {
  script: {
    required: true,
    trigger: ["input", "blur"],
  },
  search: {
    required: true,
    trigger: ["input", "blur"],
  },
};

const HandleGenerateSubject = async () => {
  try {
    isLoading.value = !isLoading.value;
    const { data } = await $fetch<{
      data: { script: string; search: string[] };
    }>(`${API_URL}/api/script`, {
      method: "POST",
      body: formModel.value,
    });
    videoModel.value.script = data.script;
    videoModel.value.search = data.search.join(",");

    activeTab.value = "review";
  } catch (error) {
    console.log({ error });
  } finally {
    isLoading.value = false;
  }
};

/*----------  Step 2  ----------*/

const HandleGenerateVideo = async () => {
  try {
    isLoading.value = !isLoading.value;
    const { data } = await $fetch<{
      data: {
        finalAudio: string;
        subtitles: string;
        finalVideo: string;
      };
    }>(`${API_URL}/api/search-and-download`, {
      method: "POST",
      body: {
        script: videoModel.value.script,
        search: videoModel.value.search.split(","),
        voice: videoModel.value.voice,
      },
    });

    finalVideo.value = data.finalVideo;
    activeTab.value = "audio";
  } catch (error) {
    console.log({ error });
  } finally {
    isLoading.value = false;
  }
};

/*----------  Add audio  ----------*/
const selectedAudio = ref("");
const HandleAddAudio = async () => {
  try {
    isLoading.value = !isLoading.value;
    const { data } = await $fetch<{ data: { finalVideo: string } }>(
      `${API_URL}/api/addAudio`,
      {
        method: "POST",
        body: {
          finalVideo: "output.mp4",
          songPath: selectedAudio.value,
        },
      }
    );
    router.push("/videos");
  } catch (error) {
    console.log({ error });
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="mt-20">
    <n-tabs
      type="line"
      animated
      v-model:value="activeTab"
      display-directive="if"
    >
      <n-tab-pane name="script" tab="Generate script">
        <n-form
          ref="formRef"
          class="max-w-screen-md"
          :model="formModel"
          :rules="rules"
          size="large"
          :disabled="isLoading"
        >
          <n-form-item label="Model:" path="aiModel">
            <n-select v-model:value="formModel.aiModel" :options="options" />
          </n-form-item>
          <n-form-item label="Video subject:" path="videoSubject">
            <n-input
              v-model:value="formModel.videoSubject"
              placeholder="Video Subject"
              type="textarea"
              show-count
              clearable
              :autosize="{
                minRows: 10,
                maxRows: 20,
              }"
            />
          </n-form-item>
          <n-form-item label="Extra Prompt:">
            <n-input
              v-model:value="formModel.extraPrompt"
              placeholder="Video Subject"
              type="textarea"
              show-count
              clearable
            />
          </n-form-item>
          <n-form-item>
            <n-button
              @click="HandleGenerateSubject"
              type="primary"
              :loading="isLoading"
              :disabled="isLoading"
            >
              Generate script
            </n-button>
          </n-form-item>
        </n-form>
      </n-tab-pane>
      <n-tab-pane name="review" tab="Review script">
        <n-form
          ref="reviewFormRef"
          class="max-w-screen-md"
          :model="videoModel"
          :rules="videoRules"
          size="large"
          :loading="isLoading"
        >
          <n-form-item label="Voice:" path="voice">
            <n-select
              v-model:value="videoModel.voice"
              :options="voiceOptions"
            />
          </n-form-item>
          <n-form-item label="Video Script:" path="script">
            <n-input
              v-model:value="videoModel.script"
              placeholder="Video script"
              type="textarea"
              show-count
              clearable
              :autosize="{
                minRows: 10,
                maxRows: 20,
              }"
            />
          </n-form-item>
          <n-form-item label="Search terms:" path="search">
            <n-input
              v-model:value="videoModel.search"
              placeholder="Search terms"
              type="textarea"
              show-count
              clearable
            />
          </n-form-item>
          <n-form-item>
            <n-button
              @click="HandleGenerateVideo"
              type="primary"
              :loading="isLoading"
              :disabled="isLoading"
            >
              Generate the video
            </n-button>
          </n-form-item>
        </n-form>
      </n-tab-pane>
      <n-tab-pane name="audio" tab="Select audio">
        <n-form
          ref="reviewFormRef"
          class="max-w-screen-md"
          :model="videoModel"
          :rules="videoRules"
          size="large"
          :loading="isLoading"
        >
          <n-form-item label="Select audio:" path="voice">
            <n-radio-group v-model:value="selectedAudio" name="radiogroup">
              <n-space :vertical="true">
                <n-radio
                  v-for="song in availableSongs"
                  :key="song"
                  :value="song"
                  :label="song"
                />
              </n-space>
            </n-radio-group>
          </n-form-item>
          <div>
            <audio
              controls
              v-for="song in availableSongs"
              :key="song"
              class="mb-5"
            >
              <source
                :src="`${API_URL}/static/Songs/${song}`"
                type="audio/mp4"
              />
            </audio>
          </div>
          <n-form-item>
            <n-button
              @click="HandleAddAudio"
              type="primary"
              :loading="isLoading"
              :disabled="isLoading"
            >
              Add audio
            </n-button>
          </n-form-item>
        </n-form>
      </n-tab-pane>
    </n-tabs>
  </div>
</template>
<style scoped></style>
