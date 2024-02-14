<script lang="ts" setup>
/**
 *
 * Global Settings
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */

const isLoading = ref(false);
const API_URL = "http://localhost:8080";

const globalSettings = useLocalStorage("globalSettings", {
  font: "Roboto",
  fontColor: "#000",
  subtitlePosition: "center,bottom",
});

const settingsRule = {
  font: {
    required: true,
    trigger: ["input", "blur"],
  },
  fontColor: {
    required: true,
    trigger: ["input", "blur"],
  },
  subtitlePosition: {
    required: true,
    trigger: ["input", "blur"],
  },
};

const subtitlePositionOptions = [
  "center,top",
  "center,bottom",
  "center,center",
  "left,center",
  "left,bottom",
  "right,center",
  "right,bottom",
];

const HandleSaveSettings = async () => {
  //   Save the setting to local storage
};
</script>

<template>
  <div class="min-h-screen flex flex-col justify-center items-center">
    <header class="text-3xl leading-10 font-bold">Global Settings</header>

    <n-form
      ref="formRef"
      class="max-w-screen-md mt-10"
      :model="globalSettings"
      :rules="settingsRule"
      size="large"
      :disabled="isLoading"
    >
      <n-form-item label="Font:" path="font">
        <n-input
          v-model:value="globalSettings.font"
          placeholder="Font for the subtitle"
          show-count
          clearable
        />
      </n-form-item>
      <n-form-item label="Color(#18A058)" path="fontcolor">
        <n-color-picker
          v-model:value="globalSettings.fontColor"
          :show-alpha="false"
        />
      </n-form-item>
      <n-form-item label="Subtitle position:" path="subtitlePosition">
        <n-radio-group
          v-model:value="globalSettings.subtitlePosition"
          name="subtitlePosition"
          size="medium"
        >
          <n-radio-button
            v-for="position in subtitlePositionOptions"
            :key="position"
            :value="position"
          >
            <span class="capitalize">
              {{ position }}
            </span>
          </n-radio-button>
        </n-radio-group>
      </n-form-item>
      <n-form-item>
        <n-button
          @click="HandleSaveSettings"
          type="success"
          ghost
          :loading="isLoading"
          :disabled="isLoading"
        >
          Save settings
        </n-button>
      </n-form-item>
    </n-form>
  </div>
</template>
<style scoped></style>
