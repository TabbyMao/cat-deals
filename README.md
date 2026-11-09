# 🐾 猫猫好价 · Cat Deals

每天自动汇总 Amazon 和 Walmart 上指定品牌的**猫粮、猫砂、非处方外用驱虫药**折扣，按折扣力度分档展示。
*Automatically collects daily Amazon and Walmart discounts on selected brands of **cat food, cat litter and OTC topical flea treatments**, grouped by discount level.*

```
GitHub Actions（每天自动跑一次 / runs once a day）
   │  scripts/fetch_deals.py
   │    ├─ Amazon Creators API   ── 按品牌关键词搜索 / search by brand
   │    └─ Walmart Affiliate API ── 按品牌关键词搜索 / search by brand
   │  → 过滤 filter → 算折扣 discount → 分档 tier → 记录价格历史 price history
   ▼
public/data/deals.json ──(自动提交 auto-commit)──▶ Cloudflare Pages 自动部署 auto-deploy ──▶ 网页 website
```

> **当前状态 / Current status：** 还没有接口密钥时，网站显示**示例数据**（随机生成的价格，页面顶部有黄色提示）。按下面「申请接口权限」的步骤拿到密钥后，第二天就会换成真实折扣。
> *Until API keys are added, the site shows **demo data** (random prices, with a yellow banner at the top). Once you add keys following "Getting API access" below, real deals appear on the next run.*

---

## 目录 / Contents

1. [文件说明 / Files](#1-文件说明--files)
2. [折扣怎么算 / How discounts are calculated](#2-折扣怎么算--how-discounts-are-calculated)
3. [申请 Amazon 接口 / Amazon API access](#3-申请-amazon-接口--amazon-api-access)
4. [申请 Walmart 接口 / Walmart API access](#4-申请-walmart-接口--walmart-api-access)
5. [把密钥填进 GitHub / Add keys to GitHub](#5-把密钥填进-github--add-keys-to-github)
6. [检查是否成功 / Verify it works](#6-检查是否成功--verify-it-works)
7. [备选方案 / Plan B](#7-备选方案--plan-b)
8. [常见调整 / Customizing](#8-常见调整--customizing)
9. [已知限制 / Known limitations](#9-已知限制--known-limitations)

---

## 1. 文件说明 / Files

| 文件 File | 作用 Purpose |
|---|---|
| `config/brands.json` | **品牌清单和折扣档位**，增删品牌、改档位只改这里<br>*Brand list and discount tiers — the only file to edit when changing brands or tiers* |
| `scripts/fetch_deals.py` | 每日抓取主程序 *Daily fetch script* |
| `scripts/providers/` | Amazon、Walmart 接口，以及示例数据 *Amazon / Walmart API clients and the demo data generator* |
| `public/` | 网页 `index.html` / `style.css` / `app.js`，读取 `public/data/deals.json`<br>*The website, which reads `public/data/deals.json`* |
| `data/history.json` | 每个商品每天的价格，用于「30天最低价」和补全原价<br>*Daily price of every product, used for "30-day low" and missing list prices* |
| `.github/workflows/daily.yml` | 每天定时运行的任务 *The daily scheduled job* |
| `tests/` | 单元测试 *Unit tests* |

---

## 2. 折扣怎么算 / How discounts are calculated

- **折扣 = 现价 ÷ 原价。** 原价优先用商家标的划线价（Amazon 的 List Price / Was Price，Walmart 的 MSRP）。
  *Discount = current price ÷ original price. The original price is the store's strike-through price (Amazon List/Was Price, Walmart MSRP).*
- 商家没标原价时（Walmart 常见），用本站记录的**近 30 天最高价**，至少要有 3 天记录才会用。所以网站刚上线时，Walmart 的折扣会比较少。
  *If the store shows no original price (common on Walmart), the site uses its own **30-day high**, once it has at least 3 days of history. Expect few Walmart deals in the first days.*
- 档位 Tiers：5折及以下 (≥50% off) · 5–6折 (40–50% off) · 6–7折 (30–40% off) · 7–8折 (20–30% off) · 8–9折 (10–20% off) · 9折以上 (<10% off)。在 `config/brands.json` 的 `tiers` 里可以改。*Editable under `tiers`.*
- 「30天最低」：今天的价格 ≤ 过去 30 天每天的价格，并且至少有 7 天记录。
  *"30-day low": today's price ≤ every price in the past 30 days, with at least 7 days of history.*
- **Subscribe & Save 订阅价**：Amazon 接口会把订阅价作为单独一条报价返回，网页上显示为绿色的「订阅价」。勾选「按订阅价算折扣」后，按订阅价分档。
  *Amazon returns Subscribe & Save as a separate offer; the site shows it in green, and the "按订阅价算折扣" switch ranks deals by the subscription price.*

---

## 3. 申请 Amazon 接口 / Amazon API access

> ⚠️ **门槛 / Requirement：** Creators API 要求 Associates 账户**在过去 30 天内有至少 10 笔合格销售**，之后销量不够还会暂停权限，销量恢复后自动恢复。新账户还要在开户后 **180 天内至少有 3 笔销售**，否则会被关闭。整个过程可能需要几周到几个月。
> *Creators API requires **at least 10 qualifying sales in the past 30 days**; access pauses if sales drop and resumes automatically. New Associates accounts must also make **3 qualifying sales within 180 days** or they are closed. Expect weeks to months.*

### 3.1 注册 Amazon Associates / Sign up for Amazon Associates

1. 打开 https://affiliate-program.amazon.com ，点 **Sign up**，用你的 Amazon 账号登录。
   *Go to the site, click **Sign up**, and log in with your Amazon account.*
2. **账户信息**：填姓名、地址、电话。
   *Account info: name, address, phone.*
3. **网站列表**：填你的 `xxx.pages.dev` 网址；有小红书、Instagram 等账号也可以加上。
   *Website list: add your `xxx.pages.dev` URL, plus any social accounts.*
4. **Store ID**：起一个名字，比如 `tabbymao-20`，后面要填的 `AMAZON_PARTNER_TAG` 就是它。
   *Pick a Store ID such as `tabbymao-20` — this is your `AMAZON_PARTNER_TAG`.*
5. 回答网站内容和流量来源的问题，如实填写。
   *Answer the questions about your content and traffic honestly.*
6. 填付款和税务信息（W-9 表）。
   *Fill in payment and tax info (Form W-9).*

### 3.2 攒够销售 / Get qualifying sales

- 登录 Amazon 后，商品页顶部有 **SiteStripe** 工具条，点 **Get Link → Text**，就能拿到带你推广标签的链接。
  *While logged in, the **SiteStripe** bar at the top of product pages → **Get Link → Text** gives a link with your tag.*
- 把链接分享给朋友、猫友群、小红书等地方。
  *Share links with friends, cat-owner groups, social media.*
- ❌ **不能用自己的链接给自己买东西**：违反 Associates 规定，也不算数。也不能用返现、礼物之类的好处诱导别人点链接购买。
  *Do **not** buy through your own links (against the rules and not counted), and do not offer incentives for clicks or purchases.*
- 网页底部已经放了 Amazon 要求的披露声明：*As an Amazon Associate I earn from qualifying purchases.*
  *The required disclosure is already in the site footer.*

### 3.3 创建 Creators API 凭证 / Create Creators API credentials

1. 达到门槛后，登录 Associates Central，顶部菜单 **Tools → Creators API**。只有账户主人能操作。
   *Once eligible: Associates Central → **Tools → Creators API** (primary account owner only).*
2. 创建 Application，再创建凭证（Credential）。
   *Create an application, then a credential.*
3. 复制 **Client ID（Credential ID）** 和 **Client Secret**。⚠️ Secret 可能只显示一次，马上存好。
   *Copy the **Client ID** and **Client Secret**. The secret may be shown only once.*
4. 原来 PA-API 的 AWS Access Key / Secret Key **不能用**，必须用新创建的凭证。
   *Old PA-API AWS keys do **not** work; you must create new credentials.*

---

## 4. 申请 Walmart 接口 / Walmart API access

> ⚠️ 有第三方资料说 Walmart 已经不再发放新的 Affiliate API 密钥，Walmart 官方没有证实。先试一下；如果 walmart.io 上找不到申请入口，或者一直拿不到 Consumer ID，看第 7 节的备选方案。
> *Some third-party docs say Walmart no longer issues new Affiliate API keys (not confirmed by Walmart). Try it; if walmart.io has no way to apply or never shows a Consumer ID, see section 7.*

### 4.1 生成密钥 / Generate a key pair

在 Mac 的「终端」(Terminal) 里逐行运行 / *Run in Terminal on your Mac:*

```bash
cd ~/Documents
openssl genrsa -out walmart_private.pem 2048
openssl rsa -in walmart_private.pem -pubout -out walmart_public.pem
pbcopy < walmart_public.pem      # 复制公钥 / copies the PUBLIC key
```

- `walmart_public.pem` = **公钥 public key**，上传给 Walmart。*Upload to Walmart.*
- `walmart_private.pem` = **私钥 private key**，❌ **绝对不要上传到仓库或发给别人**，只放进 GitHub Secret（第 5 节）。`.gitignore` 已经排除了 `*.pem` 文件。
  *❌ **Never commit or share it**; it only goes into a GitHub Secret (section 5). `.gitignore` already excludes `*.pem`.*

### 4.2 在 walmart.io 拿 Consumer ID / Get a Consumer ID on walmart.io

1. 打开 https://walmart.io ，注册并登录。*Sign up and log in.*
2. 左侧菜单 **Applications** → 创建一个应用。*Create an application.*
3. 点 **Upload/Update public key** → Environment 选 **Production** → 粘贴刚才复制的公钥 → 保存。
   *Choose **Production**, paste the public key, save.*
4. 回到面板，复制 **Consumer ID**；**Key Version** 一般是 `1`。
   *Copy the **Consumer ID**; Key Version is usually `1`.*
5. 拿不到 Consumer ID 时，常见原因 / *If no Consumer ID appears, common causes:*
   - 粘贴时多了空格或空行 *extra spaces / blank lines in the paste*
   - 误传了私钥 *pasted the private key by mistake*
   - 重复上传了同一个公钥 *re-uploaded the same public key*

### 4.3 加入 Walmart 推广计划（可选）/ Join the Walmart affiliate program (optional)

1. 到 https://impact.com 注册 **Partner** 账号。*Sign up as a **Partner**.*
2. 搜索 **Walmart** 并申请加入；审核可能要几天，新网站有可能被拒。
   *Search for **Walmart** and apply; approval can take days and new sites may be rejected.*
3. 通过后，在账户右上角找到 **Publisher ID**。没有它网站照样能运行，只是链接不带推广追踪，没有佣金。
   *Your **Publisher ID** is in the top-right of your account. Without it the site still works, just with no commission tracking.*

---

## 5. 把密钥填进 GitHub / Add keys to GitHub

GitHub 仓库 → **Settings → Secrets and variables → Actions → New repository secret**，逐个添加。哪家拿到就先填哪家，另一家没填会自动跳过。
*Repository → **Settings → Secrets and variables → Actions → New repository secret**. Add whichever store you have; the other is skipped.*

| Name | 填什么 / Value |
|---|---|
| `AMAZON_CLIENT_ID` | Amazon Client ID |
| `AMAZON_CLIENT_SECRET` | Amazon Client Secret |
| `AMAZON_PARTNER_TAG` | Store ID，如 / e.g. `tabbymao-20` |
| `WALMART_CONSUMER_ID` | walmart.io Consumer ID |
| `WALMART_KEY_VERSION` | `1` |
| `WALMART_PRIVATE_KEY` | 终端运行 `pbcopy < ~/Documents/walmart_private.pem` 后粘贴，**包括** `-----BEGIN…` 和 `-----END…` 两行<br>*Run that command, then paste — **including** the BEGIN/END lines* |
| `WALMART_PUBLISHER_ID` | Impact Publisher ID（可选 / optional） |

⚠️ 注意事项 / Notes:
- Secret 保存后就看不到内容了，只能覆盖。*Secrets can't be viewed after saving, only replaced.*
- 名字必须和上表**完全一致**（全大写）。*Names must match exactly (uppercase).*
- 不要把任何密钥写进代码文件或 README。*Never put keys in code or this README.*

---

## 6. 检查是否成功 / Verify it works

1. 仓库 → **Actions → Daily cat deals → Run workflow → Run workflow**。
2. 点进这次运行 → 展开 **Fetch deals** 步骤，正常会看到 / *Open the run → expand **Fetch deals**; you should see:*
   ```
   2026-11-10: 412 matching products, 63 on sale
     Amazon: ok, 268 matched, 0 errors
     Walmart: ok, 144 matched, 0 errors
   ```
3. 网站上的黄色「示例数据」提示消失，就说明成功了。之后每天美东早上 6–7 点自动更新。
   *The yellow demo banner disappears. After that it updates every morning (~6–7 am ET).*

常见报错 / Common errors:

| 日志里看到 Log shows | 意思 Meaning | 怎么办 What to do |
|---|---|---|
| `AssociateNotEligible` | Amazon 30 天销售不足 10 笔 *Fewer than 10 sales in 30 days* | 继续攒销售，达标后自动恢复 *Keep earning sales; access resumes automatically* |
| `HTTP 401` / `invalid_client` | Amazon ID 或 Secret 填错 *Wrong Amazon ID/secret* | 重新复制粘贴，检查有没有多余空格 *Re-paste; check for spaces* |
| `HTTP 404`（Amazon） | 搜索接口地址变了 *Search URL changed* | 新增 Secret `AMAZON_SEARCH_URL`，填 Amazon 文档里 SearchItems 的地址 *Add the current SearchItems URL as a secret* |
| `Could not authenticate` / `HTTP 401`（Walmart） | 私钥、Consumer ID 或 Key Version 不匹配 *Key/ID mismatch* | 确认上传的公钥和填的私钥是同一对 *Make sure the uploaded public key matches the private key* |
| `No API credentials found` | 一个密钥都没读到 *No secrets found* | 检查 Secret 名字是否完全一致 *Check secret names* |

---

## 7. 备选方案 / Plan B

如果两边都拿不到官方接口，可以改用第三方数据服务（比如 Apify 这类按条数收费的平台）：不用申请，当天就能用。缺点是要持续付费，大约每月几美元到几十美元，取决于抓多少；而且这类服务本质上是抓取网页，不是 Amazon 和 Walmart 官方许可的方式。需要时只要新增一个 `scripts/providers/` 适配器，网站其他部分不用改。
*If neither official API works out, a third-party data service (e.g. pay-per-result platforms like Apify) works the same day with no approval. Downsides: ongoing cost (roughly a few to a few tens of dollars a month depending on volume), and these services scrape pages, which isn't officially sanctioned by Amazon or Walmart. Only a new adapter in `scripts/providers/` is needed; nothing else changes.*

---

## 8. 常见调整 / Customizing

- **加品牌 Add a brand**：在 `config/brands.json` 的 `brands` 里加一行；`queries` 是搜索词，`match` 是标题里必须出现的词。
  *Add an entry under `brands`; `queries` = search terms, `match` = words that must appear in the title.*
- **搜到不相关商品 Irrelevant results**：在对应类别的 `exclude_any` 里加关键词。*Add words to the category's `exclude_any`.*
- **改运行时间 Change schedule**：改 `.github/workflows/daily.yml` 里的 `cron`（UTC 时间）。*Edit `cron` (UTC).*
- **本地预览 Preview locally**：
  ```bash
  python3 scripts/fetch_deals.py --demo
  python3 -m http.server -d public 8000   # 打开 open http://localhost:8000
  ```

---

## 9. 已知限制 / Known limitations

- 接口返回的订阅价是基础折扣，同一次送货订满 5 件以上的额外折扣不包括在内；「Clip coupon」优惠券也拿不到，所以实际到手价可能更低。
  *Subscribe & Save shows the base discount (not the extra discount for 5+ subscriptions); clip coupons aren't available, so the real price may be lower.*
- 每个关键词只抓前 30 条（Amazon）/ 50 条（Walmart），冷门规格可能漏掉。
  *Only the top 30 (Amazon) / 50 (Walmart) results per keyword are checked.*
- 每天更新一次，几小时就结束的 Lightning Deal 可能已经过期。
  *Updated once a day; short Lightning Deals may have ended.*
- 某家当天抓取完全失败时，网页会继续显示它前一天的数据，并标上「昨日数据」。
  *If a store fails entirely, yesterday's deals are kept and labeled 「昨日数据」.*
- 示例数据阶段，商品链接打开的是品牌搜索页，不是具体商品页。
  *In demo mode, links go to brand search pages, not product pages.*
