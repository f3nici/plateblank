import { createRouter, createWebHistory } from 'vue-router'
import UploadView from './views/UploadView.vue'
import AnnotateView from './views/AnnotateView.vue'
import ResultsView from './views/ResultsView.vue'

const routes = [
  { path: '/', component: UploadView },
  { path: '/annotate', component: AnnotateView },
  { path: '/annotate/:id', component: AnnotateView },
  { path: '/results', component: ResultsView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
