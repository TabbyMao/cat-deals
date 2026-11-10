# 🐾 猫猫好价 · Cat Deals

🌐 **网站 / Website：https://cat-deals.pages.dev**

**[中文说明](#中文说明) · [English Guide](#english-guide)**

---

# 中文说明

每天自动汇总 Amazon 和 Walmart 上指定品牌的**猫粮、猫砂、非处方外用驱虫药**折扣，按折扣力度分档展示。

~~~
GitHub Actions（每天自动运行一次）
   │  scripts/fetch_deals.py
   │    ├─ Amazon Creators API   ── 按品牌关键词搜索
   │    └─ Walmart Affiliate API ── 按品牌关键词搜索
   │  → 过滤 → 算折扣 → 分档 → 记录价格历史
   ▼
public/data/deals.json ──（自动提交）──▶ Cloudflare Pages 自动部署 ──▶ 网站
~~~

> **当前状态：** 还没有接口密钥时，网站显示**示例数据**（随机价格，页面顶部有黄色提示）。按下面第 3–5 节拿到密钥并填好后，下一次运行就会换成真实折扣。

## 1. 文件说明

| 文件 | 作用 |
|---|---|
| `config/brands.json` | **品牌清单和折扣档位**，增删品牌、改档位只改这里 |
| `scripts/fetch_deals.py` | 每日抓取主程序 |
| `scripts/providers/` | Amazon、Walmart 接口，以及示例数据 |
| `public/` | 网页（`index.html` / `style.css` / `app.js`），读取 `public/data/deals.json` |
| `data/history.json` | 每个商品每天的价格，用于「30天最低价」和补全原价 |
| `.github/workflows/daily.yml` | 每天定时运行的任务 |
| `tests/` | 单元测试 |

## 2. 折扣怎么算

- **折扣 = 现价 ÷ 原价。** 原价优先用商家标的划线价（Amazon 的 List Price / Was Price，Walmart 的 MSRP）。
- 商家没标原价时（Walmart 常见），用本站记录的**近 30 天最高价**，至少要有 3 天记录。所以刚上线时 Walmart 的折扣会比较少。
- 档位：5折及以下 · 5–6折 · 6–7折 · 7–8折 · 8–9折 · 9折以上。可在 `config/brands.json` 的 `tiers` 里修改。
- 「30天最低」：今天的价格 ≤ 过去 30 天每天的价格，且至少有 7 天记录。
- **订阅价（Subscribe & Save）**：Amazon 接口会把订阅价作为单独一条报价返回，网页上显示为绿色的「订阅价」。勾选「按订阅价算折扣」后，按订阅价分档。

## 3. 申请 Amazon 接口

> ⚠️ **门槛：** Creators API 要求 Associates 账户**过去 30 天内至少 10 笔合格销售**；销量不足时权限会暂停，恢复后自动开通。新账户还必须在开户后 **180 天内至少有 3 笔销售**，否则会被关闭。整个过程可能要几周到几个月。

### 3.1 注册 Amazon Associates

1. 打开 https://affiliate-program.amazon.com ，点 **Sign up**，用你的 Amazon 账号登录。
2. 填写姓名、地址、电话。
3. 网站列表填 `https://cat-deals.pages.dev`；有小红书、Instagram 等账号也可以加上。
4. 设置 Store ID，比如 `tabbymao-20`，它就是后面的 `AMAZON_PARTNER_TAG`。
5. 如实回答网站内容和流量来源的问题。
6. 填写付款和税务信息（W-9 表）。

### 3.2 攒够销售

- 登录 Amazon 后，商品页顶部有 **SiteStripe** 工具条，点 **Get Link → Text**，就能拿到带推广标签的链接。
- 把链接分享给朋友、猫友群、小红书等。
- ❌ **不能用自己的链接给自己买东西**，这违反规定，也不算数；也不能用返现、礼物等好处诱导别人购买。
- 网站底部已经放了 Amazon 要求的披露声明。

### 3.3 创建 Creators API 凭证

1. 达到门槛后，登录 Associates Central → 顶部菜单 **Tools → Creators API**。只有账户主人能操作。
2. 创建 Application，再创建凭证（Credential）。
3. 复制 **Client ID** 和 **Client Secret**。⚠️ Secret 可能只显示一次，马上存好。
4. 旧 PA-API 的 AWS Access Key 不能用，必须用新创建的凭证。

## 4. 申请 Walmart 接口

> ⚠️ 有第三方资料说 Walmart 已不再发放新的 Affiliate API 密钥，Walmart 官方没有证实。可以先试一下；如果 walmart.io 上找不到申请入口，或一直拿不到 Consumer ID，请看第 7 节的备选方案。

### 4.1 生成密钥（Windows）

1. 如果电脑上还没有 **Git Bash**，先安装 Git for Windows（https://git-scm.com ，安装时一路默认），它自带 openssl。
2. 在「文档」文件夹空白处右键 → **Open Git Bash here**（Windows 11 要先点「显示更多选项」），逐行运行：

~~~bash
openssl genrsa -out walmart_private.pem 2048
openssl rsa -in walmart_private.pem -pubout -out walmart_public.pem
clip < walmart_public.pem
~~~

最后一行会把**公钥**复制到剪贴板。

- `walmart_public.pem` 是**公钥**，要上传给 Walmart。
- `walmart_private.pem` 是**私钥**。❌ **绝对不要上传到仓库或发给别人**，只能填进 GitHub Secret（第 5 节）。`.gitignore` 已经排除了 `*.pem` 文件。

### 4.2 在 walmart.io 拿 Consumer ID

1. 打开 https://walmart.io ，注册并登录。
2. 左侧菜单 **Applications** → 创建一个应用。
3. 点 **Upload/Update public key** → Environment 选 **Production** → 粘贴公钥 → 保存。
4. 回到面板，复制 **Consumer ID**；**Key Version** 一般是 `1`。
5. 拿不到 Consumer ID 的常见原因：粘贴时多了空格或空行、误传了私钥、重复上传了同一个公钥。

### 4.3 加入 Walmart 推广计划（可选）

1. 到 https://impact.com 注册 **Partner** 账号。
2. 搜索 **Walmart** 并申请加入。审核可能要几天，新网站可能被拒。
3. 通过后，在账户右上角找到 **Publisher ID**。不填也能运行，只是链接没有推广追踪，也就没有佣金。

## 5. 把密钥填进 GitHub

仓库 → **Settings → Secrets and variables → Actions → New repository secret**，逐个添加。哪家拿到就先填哪家，没填的那家会自动跳过。

| 名称 | 填什么 |
|---|---|
| `AMAZON_CLIENT_ID` | Amazon Client ID |
| `AMAZON_CLIENT_SECRET` | Amazon Client Secret |
| `AMAZON_PARTNER_TAG` | Store ID，如 `tabbymao-20` |
| `WALMART_CONSUMER_ID` | walmart.io 的 Consumer ID |
| `WALMART_KEY_VERSION` | `1` |
| `WALMART_PRIVATE_KEY` | 在 Git Bash 运行 `clip < walmart_private.pem` 后粘贴，**包括** `-----BEGIN…` 和 `-----END…` 两行 |
| `WALMART_PUBLISHER_ID` | Impact Publisher ID（可选） |

注意：
- Secret 保存后就看不到内容了，只能覆盖。
- 名字必须和上表**完全一致**（全大写）。
- 不要把任何密钥写进代码或 README。

## 6. 检查是否成功

1. 仓库 → **Actions → Daily cat deals → Run workflow → Run workflow**。
2. 点进这次运行 → 展开 **Fetch deals** 步骤，正常会看到：
   ~~~
   2026-11-10: 412 matching products, 63 on sale
     Amazon: ok, 268 matched, 0 errors
     Walmart: ok, 144 matched, 0 errors
   ~~~
3. 网站上的黄色「示例数据」提示消失，就说明成功了。之后每天美东早上 6–7 点自动更新。

常见报错：

| 日志里看到 | 意思 | 怎么办 |
|---|---|---|
| `AssociateNotEligible` | Amazon 30 天内销售不足 10 笔 | 继续攒销售，达标后自动恢复 |
| `HTTP 401` / `invalid_client` | Amazon ID 或 Secret 填错 | 重新复制粘贴，检查有没有多余空格 |
| `HTTP 404`（Amazon） | 搜索接口地址变了 | 新增 Secret `AMAZON_SEARCH_URL`，填 Amazon 文档里 SearchItems 的地址 |
| `HTTP 401`（Walmart） | 私钥、Consumer ID 或 Key Version 不匹配 | 确认上传的公钥和填的私钥是同一对 |
| `No API credentials found` | 一个密钥都没读到 | 检查 Secret 名字是否完全一致 |

## 7. 备选方案

如果两边都拿不到官方接口，可以改用第三方数据服务（比如 Apify 这类按条数收费的平台）：不用申请，当天就能用。缺点是要持续付费，大约每月几美元到几十美元，看抓取量；而且这类服务本质上是抓取网页，不是 Amazon / Walmart 官方许可的方式。需要时只要在 `scripts/providers/` 里新增一个适配器，网站其他部分不用改。

## 8. 常见调整

- **加品牌**：在 `config/brands.json` 的 `brands` 里加一行；`queries` 是搜索词，`match` 是标题里必须出现的词。
- **搜到不相关商品**：在对应类别的 `exclude_any` 里加关键词。
- **改运行时间**：修改 `.github/workflows/daily.yml` 里的 `cron`（UTC 时间）。
- **本地预览**：
  ~~~bash
  python scripts/fetch_deals.py --demo
  python -m http.server -d public 8000   # 然后打开 http://localhost:8000
  ~~~

## 9. 已知限制

- 订阅价只是基础折扣，同一次送货订满 5 件以上的额外折扣不包括在内；「Clip coupon」优惠券也拿不到，实际到手价可能更低。
- 每个关键词只抓前 30 条（Amazon）/ 50 条（Walmart），冷门规格可能漏掉。
- 每天只更新一次，几小时就结束的 Lightning Deal 可能已经过期。
- 某家当天抓取完全失败时，网页会继续显示它前一天的数据，并标上「昨日数据」。
- 示例数据阶段，商品链接打开的是品牌搜索页，不是具体商品页。

---

# English Guide

Automatically collects daily Amazon and Walmart discounts on selected brands of **cat food, cat litter and OTC topical flea treatments**, grouped by discount level.

~~~
GitHub Actions (runs once a day)
   │  scripts/fetch_deals.py
   │    ├─ Amazon Creators API   ── search by brand
   │    └─ Walmart Affiliate API ── search by brand
   │  → filter → compute discount → tier → record price history
   ▼
public/data/deals.json ──(auto-commit)──▶ Cloudflare Pages auto-deploy ──▶ website
~~~

> **Current status:** Until API keys are added, the site shows **demo data** (random prices, with a yellow banner at the top). Once you add keys following sections 3–5, real deals appear on the next run.

## 1. Files

| File | Purpose |
|---|---|
| `config/brands.json` | **Brand list and discount tiers** — the only file to edit when changing brands or tiers |
| `scripts/fetch_deals.py` | Daily fetch script |
| `scripts/providers/` | Amazon / Walmart API clients and the demo data generator |
| `public/` | The website (`index.html` / `style.css` / `app.js`), which reads `public/data/deals.json` |
| `data/history.json` | Daily price of every product, used for the 30-day low and missing list prices |
| `.github/workflows/daily.yml` | The daily scheduled job |
| `tests/` | Unit tests |

## 2. How discounts are calculated

- **Discount = current price ÷ original price.** The original price is the store's strike-through price (Amazon List / Was Price, Walmart MSRP).
- If the store shows no original price (common on Walmart), the site uses its own **30-day high**, once it has at least 3 days of history. Expect few Walmart deals in the first days.
- Tiers: ≥50% off · 40–50% off · 30–40% off · 20–30% off · 10–20% off · <10% off. Edit them under `tiers` in `config/brands.json`.
- "30-day low": today's price ≤ every daily price in the past 30 days, with at least 7 days of history.
- **Subscribe & Save:** Amazon returns the subscription price as a separate offer. The site shows it in green, and the subscription switch on the page ranks deals by that price.

## 3. Amazon API access

> ⚠️ **Requirement:** Creators API requires **at least 10 qualifying sales in the past 30 days**; access pauses if sales drop and resumes automatically. New Associates accounts must also make **3 qualifying sales within 180 days** or they are closed. Expect weeks to months.

### 3.1 Sign up for Amazon Associates

1. Go to https://affiliate-program.amazon.com, click **Sign up**, and log in with your Amazon account.
2. Fill in your name, address and phone.
3. In the website list, add `https://cat-deals.pages.dev` and any social accounts.
4. Pick a Store ID such as `tabbymao-20` — this is your `AMAZON_PARTNER_TAG`.
5. Answer the questions about your content and traffic honestly.
6. Fill in payment and tax info (Form W-9).

### 3.2 Get qualifying sales

- While logged in to Amazon, the **SiteStripe** bar at the top of product pages → **Get Link → Text** gives you a link with your tag.
- Share links with friends, cat-owner groups and social media.
- ❌ **Do not buy through your own links** (against the rules and not counted), and do not offer incentives for clicks or purchases.
- The required Amazon disclosure is already in the site footer.

### 3.3 Create Creators API credentials

1. Once eligible: Associates Central → **Tools → Creators API** (primary account owner only).
2. Create an application, then a credential.
3. Copy the **Client ID** and **Client Secret**. ⚠️ The secret may be shown only once.
4. Old PA-API AWS keys do not work; you must create new credentials.

## 4. Walmart API access

> ⚠️ Some third-party docs say Walmart no longer issues new Affiliate API keys (not confirmed by Walmart). Try it; if walmart.io has no way to apply or never shows a Consumer ID, see section 7.

### 4.1 Generate a key pair (Windows)

1. If you don't have **Git Bash**, install Git for Windows (https://git-scm.com, default options). It includes openssl.
2. Right-click an empty area of your Documents folder → **Open Git Bash here** (on Windows 11, click "Show more options" first), then run:

~~~bash
openssl genrsa -out walmart_private.pem 2048
openssl rsa -in walmart_private.pem -pubout -out walmart_public.pem
clip < walmart_public.pem
~~~

The last line copies the **public key** to your clipboard.

- `walmart_public.pem` is the **public key**, which you upload to Walmart.
- `walmart_private.pem` is the **private key**. ❌ **Never commit or share it**; it only goes into a GitHub Secret (section 5). `.gitignore` already excludes `*.pem`.

### 4.2 Get a Consumer ID on walmart.io

1. Go to https://walmart.io, sign up and log in.
2. **Applications** (left menu) → create an application.
3. **Upload/Update public key** → Environment: **Production** → paste the public key → save.
4. Copy the **Consumer ID** from the dashboard; **Key Version** is usually `1`.
5. If no Consumer ID appears: check for extra spaces or blank lines, make sure you didn't paste the private key, and don't re-upload the same public key.

### 4.3 Join the Walmart affiliate program (optional)

1. Sign up as a **Partner** at https://impact.com.
2. Search for **Walmart** and apply. Approval can take days, and new sites may be rejected.
3. Your **Publisher ID** is in the top-right of your account. Without it the site still works, just with no commission tracking.

## 5. Add keys to GitHub

Repository → **Settings → Secrets and variables → Actions → New repository secret**. Add whichever store you have; the other is skipped automatically.

| Name | Value |
|---|---|
| `AMAZON_CLIENT_ID` | Amazon Client ID |
| `AMAZON_CLIENT_SECRET` | Amazon Client Secret |
| `AMAZON_PARTNER_TAG` | Store ID, e.g. `tabbymao-20` |
| `WALMART_CONSUMER_ID` | walmart.io Consumer ID |
| `WALMART_KEY_VERSION` | `1` |
| `WALMART_PRIVATE_KEY` | Run `clip < walmart_private.pem` in Git Bash, then paste — **including** the `-----BEGIN…` and `-----END…` lines |
| `WALMART_PUBLISHER_ID` | Impact Publisher ID (optional) |

Notes:
- Secrets can't be viewed after saving, only replaced.
- Names must match the table **exactly** (uppercase).
- Never put keys in code or in this README.

## 6. Verify it works

1. Repository → **Actions → Daily cat deals → Run workflow → Run workflow**.
2. Open the run → expand the **Fetch deals** step. You should see:
   ~~~
   2026-11-10: 412 matching products, 63 on sale
     Amazon: ok, 268 matched, 0 errors
     Walmart: ok, 144 matched, 0 errors
   ~~~
3. When the yellow demo banner disappears, it's working. After that the site updates every morning around 6–7 am ET.

Common errors:

| Log shows | Meaning | What to do |
|---|---|---|
| `AssociateNotEligible` | Fewer than 10 Amazon sales in 30 days | Keep earning sales; access resumes automatically |
| `HTTP 401` / `invalid_client` | Wrong Amazon ID or secret | Re-paste and check for extra spaces |
| `HTTP 404` (Amazon) | Search URL changed | Add a secret `AMAZON_SEARCH_URL` with the current SearchItems URL from Amazon's docs |
| `HTTP 401` (Walmart) | Private key, Consumer ID or Key Version mismatch | Make sure the uploaded public key matches the private key |
| `No API credentials found` | No secrets were read | Check the secret names |

## 7. Plan B

If neither official API works out, a third-party data service (e.g. pay-per-result platforms such as Apify) works the same day with no approval. Downsides: ongoing cost (roughly a few to a few tens of dollars a month depending on volume), and these services scrape pages, which Amazon and Walmart don't officially sanction. Only a new adapter in `scripts/providers/` is needed; nothing else changes.

## 8. Customizing

- **Add a brand:** add an entry under `brands` in `config/brands.json`. `queries` are the search terms; `match` are words that must appear in the title.
- **Irrelevant results:** add words to the category's `exclude_any`.
- **Change the schedule:** edit `cron` in `.github/workflows/daily.yml` (UTC).
- **Preview locally:**
  ~~~bash
  python scripts/fetch_deals.py --demo
  python -m http.server -d public 8000   # then open http://localhost:8000
  ~~~

## 9. Known limitations

- Subscribe & Save shows the base discount only (not the extra discount for 5+ subscriptions in one delivery), and clip coupons aren't available, so the real price may be lower.
- Only the top 30 (Amazon) / 50 (Walmart) results per keyword are checked; uncommon sizes may be missed.
- Updated once a day, so short Lightning Deals may have ended.
- If a store fails entirely on a given day, yesterday's deals are kept and labeled 「昨日数据」 (yesterday's data).
- In demo mode, links go to brand search pages, not product pages.
