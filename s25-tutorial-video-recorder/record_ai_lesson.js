const { chromium } = require('playwright');

(async () => {
  // 1. Launch the browser
  // Set headless: false if you want to watch the steps while they happen
  const browser = await chromium.launch({ headless: true });

  // 2. Create a context with video recording enabled
  // This works in both headless and headed modes!
  const context = await browser.newContext({
    recordVideo: {
      dir: 'recordings/', // The folder where your video will be saved
      size: { width: 1280, height: 720 },
    }
  });

  const page = await context.newPage();

  try {
    console.log("Starting the lesson...");

    // Step 1: Navigate to an educational resource
    await page.goto('https://en.wikipedia.org/wiki/Large_language_model');
    await page.waitForTimeout(2000); // Pause so the viewer can see the page

    // Step 2: Highlight the definition for the newcomer
    await page.locator('p').first().evaluate(el => el.style.backgroundColor = 'yellow');
    console.log("Highlighting the definition of an LLM.");
    await page.waitForTimeout(3000);

    // Step 3: Scroll down to show more concepts
    await page.mouse.wheel(0, 800);
    await page.waitForTimeout(2000);

    console.log("Lesson complete!");
  } catch (error) {
    console.error("An error occurred:", error);
  } finally {
    // 3. Close the context and browser
    // The video is saved only after the context is closed.
    await context.close();
    await browser.close();

    const video = await page.video();
    if (video) {
      const path = await video.path();
      console.log(`Your recording is saved at: ${path}`);
    }
  }
})();
