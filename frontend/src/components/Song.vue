<template>
  <div class="song-lyrics">
    <h1>{{ title }}</h1>
    <h2>By {{ artist }}</h2>
    <div v-for="(section, index) in sections" :key="index" class="section">
      <div v-if="section.title" class="section-title">{{ section.title }}</div>
      <div
        v-for="(line, lineIndex) in section.lines"
        :key="lineIndex"
        class="line"
      >
        <span
          v-for="(part, partIndex) in line.parts"
          :key="partIndex"
          :class="part.root"
          >{{ part }}</span
        >
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    songData: {
      type: Object,
      required: true,
    },
  },
  computed: {
    title() {
      return this.songData.title;
    },
    artist() {
      return this.songData.artist;
    },
    sections() {
      return this.songData.sections;
    },
  },
};
</script>

<style scoped>
.song-lyrics {
  font-family: Arial, sans-serif;
}

.section {
  margin-bottom: 20px;
}

.section-title {
  font-weight: bold;
  font-size: 1.2rem;
  margin-bottom: 10px;
}

.line {
  margin-bottom: 5px;
}

.line span {
  margin-right: 5px;
}
</style>
