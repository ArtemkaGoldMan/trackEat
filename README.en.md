# trackEat

[Українська](README.md) · **English**

Calorie and macro tracking without paid apps: Claude estimates food from photos, and a Google Sheet stores the entries, calculates totals and draws charts.

## How it works

1. You photograph food in a Claude project chat (optionally adding a weight or a description).
2. Claude estimates calories and macros and shows the calculation.
3. After you confirm, it appends a row to the sheet.
4. The sheet calculates daily, weekly and monthly totals, highlights over- and under-eating, and draws charts for weight, calories, protein and waist.

## Sheets

| | Link |
|---|---|
| Example with random data for 21 days | [Open](https://docs.google.com/spreadsheets/d/1vx7z_Q0UrMAOrUVHVcDCbLGrZJeHRGuL47_ULDrv6D8/edit) |
| Empty template | [Make your own copy](https://docs.google.com/spreadsheets/d/1jmuORnlPcK1LIoxqUPPi2ncdgpgP2BfMlUyLNEWzvJs/copy) |

The sheet language is Ukrainian. The template contains these tabs: **Інструкція** (instructions), **Головна** (dashboard: tiles, tables, charts for the last 21 days and all time), **Журнал** (food log), **Дні** (days), **Тижні** (weeks), **Місяці** (months), **Вага** (weight), **Налаштування** (settings, targets are calculated automatically) and a helper tab **Дані графіків** (chart data).

## Getting started

1. Open the template link and confirm the copy. Work only in your copy.
2. In the copy, open **Налаштування** and replace the yellow cells with your own values: weight, height, age, activity factor, calorie deficit or surplus, protein and fat per kg. The basal metabolic rate formula is the male one. For women, change `+5` to `-161` at the end of the formula in cell B15.
3. In Claude, create a **project**, connect Google Sheets (Settings → Connectors) and paste the text from [docs/project-instructions.en.md](docs/project-instructions.en.md) into the project instructions, using the link to your copy.
4. In the first chat of the project, write "This is the first run". Claude will ask about your goal and details and fill in the settings itself.
5. Then photograph your food in that chat. Log your weight once a day in the morning and your waist once a week.

Button names in Claude may differ because the interface changes.

## Getting more accurate estimates

This comes from the test below.

- Give the weight of the main item, for example "chicken 150 g". This reduces the error per dish from ~28% to ~22%.
- If there was oil or sauce, give the amount: "1 tablespoon of oil". Without an amount the model assumes a full portion.
- Photograph packaged food with the weight label visible. Weigh nuts.
- At fast-food chains, name the size and the drink.
- Use Sonnet in standard mode. Extended thinking does not improve accuracy.

## How accurate is it

I tested Claude Haiku, Sonnet and Opus 5.5 on 35 photos with known calories (~4,800 responses). In short:

- A single dish from a photo alone: **~28%** mean error for Sonnet, ~31% for Opus, ~41% for Haiku.
- With the weight of the main item: ~22%. With the weight of everything: ~13%.
- Over a whole day, errors partly cancel out: ~13% from photos alone, ~6% with everything weighed.
- Packaged Snickers and Mars come out almost exactly, a Big Mac is within ±5%. Handfuls of nuts are underestimated.

Full report: [docs/benchmark.en.md](docs/benchmark.en.md). Code and data: [benchmark/](benchmark/).

## Repository contents

- [docs/](docs/): the test report and Claude project instructions (Ukrainian and English).
- [benchmark/](benchmark/): test scripts, dataset, model responses and result tables.

## Limitations

- These are rough guides, not medical advice. Photo estimates do not replace weighing.
- The test used top-down cafeteria photos from Nutrition5k and a few branded products. Ordinary angled phone photos may give different results.
- 35 photos is a small sample, so the confidence intervals are wide.
- The Nutrition5k ground truth has its own error: calories come from USDA tables for weighed ingredients.

## Credits and licenses

- Dishes and snacks from [Nutrition5k](https://github.com/google-research-datasets/Nutrition5k) (Google Research, CC BY 4.0).
- Branded product photos from Wikimedia Commons; licenses and photo page links are in `benchmark/dataset.json`. The photos themselves are not included in the repository.
- Calories for the Big Mac, fries and Coca-Cola are from the McDonald's Ukraine website.
