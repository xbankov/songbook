import { createRouter, createWebHistory } from "vue-router";
import routes from "./routes";

const router = createRouter({
  history: createWebHistory(),
  routes: routes.map((route) => ({
    name: route.name,
    path: route.path,
    component: route.component,
    beforeEnter(to, from, next) {
      document.title = route.meta.title || "Default Title";
      next();
    },
  })),
});

export default router;
