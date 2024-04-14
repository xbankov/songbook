<template>
  <div>
    <h1>Data from FastAPI Backend</h1>
    <p>{{ message }}</p>
  </div>
</template>

<script>
import apiService from "@/services/apiService";

export default {
  name: "AboutView",
  data() {
    return {
      message: "", // Initialize message as an empty string
    };
  },
  mounted() {
    this.fetchData();
  },
  methods: {
    async fetchData() {
      try {
        const response = await apiService.get("/api/about");
        this.message = response.data.message; // Update message with the data returned from the backend
      } catch (error) {
        console.error("Error fetching data:", error);
      }
    },
  },
};
</script>

<style>
/* Component-specific styles */
</style>