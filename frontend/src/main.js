import "bootstrap/dist/css/bootstrap.css";
import { createApp } from "vue";
import App from "@/App.vue";
import router from "@/routes/router";
import 'bulma/css/bulma.min.css';

const app = createApp(App);
app.use(router);
app.mount("#app");
