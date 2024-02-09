<script lang="ts" setup>
/**
 *
 * All generated videos
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */
const videos = ref([]);

const { data } = await $fetch<{ data: { videos: string[] } }>(
  "http://localhost:8080/api/getVideos"
);

videos.value = data.videos;
</script>

<template>
  <div class="py-28 px-10">
    <h1 class="text-3xl leading-10 font-bold mb-10">Generated videos</h1>
    <n-table :bordered="true" :single-line="true">
      <thead>
        <tr>
          <th>ID</th>
          <th>Path</th>
          <th>Name</th>
          <th>Link</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(video, index) in videos" :key="video">
          <td>{{ index }}</td>
          <td>{{ video }}</td>
          <td>{{ video }}-name</td>
          <td>
            <a
              :href="`http://localhost:8080/static/generated_videos/${video}`"
              target="_blank"
            >
              Open
            </a>
          </td>
        </tr>
      </tbody>
    </n-table>
  </div>
</template>
<style scoped></style>
