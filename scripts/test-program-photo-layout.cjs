// Run after the frontend build with Playwright available via NODE_PATH.
// All requests are intercepted: no production API, analytics or emails are used.
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const build = path.resolve(__dirname, "../frontend/build");
const image = `data:image/svg+xml,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800"><rect width="600" height="800" fill="#84A98C"/></svg>',
)}`;
const programs = ["short", "long", "hero", "none"].map((id) => ({
  id,
  name_cs: `Program ${id}`,
  description_cs: "Popis programu bez překrytí fotografií. ".repeat(
    id === "long" ? 45 : 1,
  ),
  duration: 90,
  age_group: "ms_3_6",
  image_url: id === "none" ? null : image,
  image_layout: id === "hero" ? "hero" : "square",
  image_focus_x: 65,
  image_focus_y: 35,
}));

(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROME_PATH
      ? { executablePath: process.env.CHROME_PATH }
      : {}),
  });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname.includes("/api/")) {
        let data = {};
        if (url.pathname.includes("/programs/public/")) data = programs;
        if (url.pathname.includes("/public/institutions/"))
          data = { name: "Testovací muzeum" };
        return route.fulfill({ json: data });
      }
      if (url.hostname === "localhost") {
        const relative = url.pathname.startsWith("/booking/")
          ? "index.html"
          : url.pathname.slice(1);
        const file = path.resolve(build, relative);
        if (
          file.startsWith(build + path.sep) &&
          fs.existsSync(file) &&
          fs.statSync(file).isFile()
        ) {
          return route.fulfill({ path: file });
        }
      }
      return route.abort();
    });
    for (const width of [1440, 1024, 768, 767, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto("http://localhost/booking/photo-layout-test");
      await page.getByTestId("program-card-long").waitFor();
      for (const id of ["short", "long", "hero"]) {
        const metrics = await page
          .getByTestId(`program-card-${id}`)
          .evaluate((card) => {
            const image = card.querySelector("img");
            const box = card.getBoundingClientRect();
            const photo = image.getBoundingClientRect();
            const description = card
              .querySelector(".whitespace-pre-line")
              .getBoundingClientRect();
            return {
              rightGap:
                box.right -
                photo.right -
                parseFloat(getComputedStyle(card).borderRightWidth),
              textRight: description.right,
              textBottom: description.bottom,
              imageLeft: photo.left,
              imageTop: photo.top,
              imageWidth: photo.width,
              imageHeight: photo.height,
              position: image.style.objectPosition,
            };
          });
        assert.equal(
          metrics.position,
          "65% 35%",
          "Crop focus must be preserved",
        );
        if (id === "hero" || width >= 768) {
          assert(
            Math.abs(metrics.rightGap) < 1,
            `${id} at ${width}px: right gap ${metrics.rightGap}px`,
          );
        }
        if (id !== "hero") {
          if (width >= 768)
            assert(
              metrics.textRight < metrics.imageLeft,
              "Photo overlaps text",
            );
          else {
            assert(
              metrics.textBottom < metrics.imageTop,
              "Mobile photo overlaps text",
            );
            assert(
              Math.abs(metrics.imageWidth - metrics.imageHeight) < 1,
              "Mobile crop must stay square",
            );
          }
        }
      }
      assert.equal(
        await page.getByTestId("program-card-none").locator("img").count(),
        0,
      );
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      );
      console.log(
        `PASS photo alignment, text separation and overflow: ${width}px`,
      );
    }
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
