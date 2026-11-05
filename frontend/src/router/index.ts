import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
  },
  {
    path: '/',
    redirect: '/songs',
  },
  {
    path: '/songs',
    name: 'Songs',
    component: () => import('../views/SongsView.vue'),
  },
  {
    path: '/songs/new',
    name: 'SongNew',
    component: () => import('../views/SongEditView.vue'),
  },
  {
    path: '/songs/:id',
    name: 'SongDetail',
    component: () => import('../views/SongDetailView.vue'),
  },
  {
    path: '/songs/:id/edit',
    name: 'SongEdit',
    component: () => import('../views/SongEditView.vue'),
  },
  {
    path: '/songbooks',
    name: 'Songbooks',
    component: () => import('../views/SongbooksView.vue'),
  },
  {
    path: '/songbooks/:id',
    name: 'SongbookDetail',
    component: () => import('../views/SongbookDetailView.vue'),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from) => {
  const auth = useAuthStore()
  if (to.name !== 'Login' && !auth.isAuthenticated) {
    return { name: 'Login' }
  }
})

export default router
