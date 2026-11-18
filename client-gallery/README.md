# Client galleries

A private page for each photoshoot: the client scrolls through the photos, opens them large and downloads
the **originals in 100% quality** (files are copied byte for byte, nothing is compressed). There is a
"Download all" button (one ZIP) and, on phones, "Save to Photos".

Hosting: **Cloudflare Pages**, free, no bank card, unlimited traffic.
Each client gets their own link, for example `https://anna-3f9a1c.pages.dev`.
Pages are hidden from Google (noindex) and the name has a random code, so they can only be found through the link.

## Making a new gallery

1. Open the builder: **teophotosss.netlify.app/client-gallery/**
2. Type the client name (and, if you like, a shoot title and date), drop in the photos, click the one that should be the cover.
3. Press **Create gallery**: a ZIP downloads. The photos are not uploaded anywhere; everything is put together in your browser.
4. In Cloudflare: **Workers & Pages → Create → Pages → Upload assets**, use the project name the builder suggests,
   drop in the ZIP, **Deploy**. If Cloudflare refuses a large ZIP, unzip it and drop the folder instead.
5. Send the client the link `https://<name>.pages.dev`.

The first time, sign up for free at dash.cloudflare.com (email only, no card).

## By hand, with the script

**Build a gallery** (needs Python 3 and `pip3 install pillow`):

```
python3 client-gallery/make_gallery.py ~/Downloads/anna --client "Anna" --title "Autumn session" --date "10.11.2026"
```

The folder appears in `client-gallery/out/anna-xxxxxx/`. Page language: `--lang en` (default), `uk` or `es`.
Cover: `--cover DSC09716_edit.jpg` (default: the first photo).

Then do step 4 above, dropping in the folder.

To delete an old shoot: open the project in Cloudflare → Settings → Delete project.

## Limits

- Cloudflare Pages takes files up to 25 MB, so photos over 24 MB are stored in parts and joined back in the client's browser:
  the client still downloads one file, identical to your original. Videos are not supported yet.
- Drag-and-drop takes up to 1000 files, which is up to about 490 photos per gallery (each photo = original + 1 preview,
  and a photo over 24 MB counts as one file per 24 MB).
  For bigger shoots: `npx wrangler pages deploy client-gallery/out/<name> --project-name <name>`.
- The "Download all" ZIP is built in the client's browser, so on phones big shoots are better saved with "Save to Photos" or one by one.
