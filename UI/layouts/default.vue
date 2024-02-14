<script lang="ts" setup>
/**
 *
 * Component Description:Desc
 *
 * @author Reflect-Media <reflect.media GmbH>
 * @version 0.0.1
 *
 * @todo [ ] Test the component
 * @todo [ ] Integration test.
 * @todo [✔] Update the typescript.
 */
import type { MenuLinkRoute } from "@bg-dev/nuxt-naiveui";

const menuOptions: MenuLinkRoute[] = [
  {
    label: "Settings",
    path: "/settings",
    icon: "mdi:gamepad-circle",
  },
  {
    label: "Generate script",
    path: "/",
    icon: "mdi:script-text-outline",
  },
  {
    label: "Generated videos",
    icon: "material-symbols:slow-motion-video-rounded",
    path: "/videos",
  },
  {
    label: "Documentation",
    icon: "material-symbols:description-rounded",
    path: "/docs",
  },
];
</script>

<template>
  <NaiveLayoutSidebar has-sider position="absolute" :routes="menuOptions">
    <template #start>
      <h1 class="text-3xl leading-10 font-bold">Money Printer</h1>
    </template>
    <div class="min-h-screen bg-gray-100">
      <slot></slot>
    </div>
  </NaiveLayoutSidebar>
</template>
<style scoped></style>
