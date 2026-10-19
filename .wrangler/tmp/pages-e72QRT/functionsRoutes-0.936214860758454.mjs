import { onRequestPost as __api_contact_js_onRequestPost } from "/home/claude/ai-occupation-map/functions/api/contact.js"
import { onRequestPost as __api_e_js_onRequestPost } from "/home/claude/ai-occupation-map/functions/api/e.js"
import { onRequestGet as __api_stats_js_onRequestGet } from "/home/claude/ai-occupation-map/functions/api/stats.js"
import { onRequestPost as __api_subscribe_js_onRequestPost } from "/home/claude/ai-occupation-map/functions/api/subscribe.js"

export const routes = [
    {
      routePath: "/api/contact",
      mountPath: "/api",
      method: "POST",
      middlewares: [],
      modules: [__api_contact_js_onRequestPost],
    },
  {
      routePath: "/api/e",
      mountPath: "/api",
      method: "POST",
      middlewares: [],
      modules: [__api_e_js_onRequestPost],
    },
  {
      routePath: "/api/stats",
      mountPath: "/api",
      method: "GET",
      middlewares: [],
      modules: [__api_stats_js_onRequestGet],
    },
  {
      routePath: "/api/subscribe",
      mountPath: "/api",
      method: "POST",
      middlewares: [],
      modules: [__api_subscribe_js_onRequestPost],
    },
  ]