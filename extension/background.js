import {initContextMenus} from "./features/context-menu.js";
import { initDownloads } from "./features/downloads.js";
import { initDoubanChart } from "./features/douban-books/chart-sync.js";
import { initDoubanLatest } from "./features/douban-books/latest-sync.js";

initContextMenus();
initDownloads();
initDoubanChart();
initDoubanLatest();
