# ChineseVerse mobile app (Android and iOS)

The Android and iOS apps are the same React frontend as the website, packaged
with [Capacitor 8](https://capacitorjs.com/). They talk to the same FastAPI
backend and database, with the same accounts, progress, Learning DNA,
companions, translations (EN / RU / TG / ZH) and themes. The website is not
replaced: it still builds and deploys exactly as before.

```
frontend/
  capacitor.config.json   app id, name, splash and system-bar settings
  android/                Android Studio / Gradle project (committed)
  ios/                    Xcode project, Swift Package Manager (committed)
  store-assets/           artwork uploaded to the stores by hand
  src/platform.js         "am I the website or the app?" + the API address
  src/native.js           status bar, safe areas, Android back button, splash
  src/nativeSpeech.js     the phone's text-to-speech engine
```

## Why Capacitor

- It wraps the existing Vite build: no second codebase, and every page,
  exercise and translation is the one the website ships.
- One `android/` and one `ios/` project come out of the same source.
- The app bundles its pages (it does not just open the website in a frame),
  so it starts without the network, keeps the learner signed in offline and
  uses native speech. That is also what Apple's review guideline 4.2
  ("minimum functionality") expects of an app built on web technology.
- React Native or Flutter would have meant rewriting every page.

## How the app differs from the website

| Area | Website | App |
|---|---|---|
| Where pages come from | nginx | bundled in the app (`https://localhost` on Android, `capacitor://localhost` on iOS) |
| API | same-origin `/api` | `https://chineseverse.qobus.tj/api` (`src/platform.js`) |
| CORS | `CORS_ORIGINS` | plus `MOBILE_APP_ORIGINS` (backend `config.py`, on by default) |
| Uploaded avatars | `/static/...` | resolved against the API (`assetUrl`) |
| Chinese audio | `speechSynthesis` | the phone's TTS engine (`@capacitor-community/text-to-speech`) |
| Speaking answers | Web Speech recognizer | the phone's recognizer (`@capgo/capacitor-speech-recognition`) |
| Tone Coach recording | `getUserMedia` | the same, in the WebView (microphone permission) |
| Google / GitHub sign-in | yes | **hidden** (see Limitations) |
| `/` | landing page | sign-in, or the dashboard when signed in |
| Status bar, notch, home indicator | n/a | `src/native.js` + "Mobile app" section of `index.css` |
| Android back button | n/a | walks back through the app; leaves on the first screen |

Two changes reach the website as well, because they help both:

- **Offline at start-up keeps you signed in.** Boot used to sign the learner
  out whenever `GET /api/me` failed for any reason, no network included. Now
  only a 401/403 from the server ends the session (`App.jsx`).
- **An offline notice** (`NetworkBanner.jsx`) appears while the device has no
  connection, in all four languages.

The session is the same JWT as on the website (7 days), kept in the
WebView's `localStorage` under the same keys. Android cloud backup is off
(`android:allowBackup="false"`), so the token is not copied into Google
backups. Answers are graded and stored by the server only, so going offline
mid-exercise never leaves half-saved progress on the phone. The request
simply fails with the localized "can't reach ChineseVerse" message.

## Identifiers

| | Value |
|---|---|
| App name | ChineseVerse |
| Android `applicationId` / iOS bundle id | `tj.qobus.chineseverse` |
| Version | `1.0` (Android `versionCode 1`, iOS `MARKETING_VERSION 1.0`, build 1) |

The id cannot change after the first store upload. Raise `versionCode` (Android,
`android/app/build.gradle`) and the build number (Xcode → target → General)
for every upload.

## Everyday workflow

From `frontend/`:

```
npm run mobile:sync      # vite build + copy into android/ and ios/ + update plugins
npm run mobile:android   # open the project in Android Studio
npm run mobile:ios       # open the project in Xcode (macOS only)
```

Run `mobile:sync` after every frontend change you want in the app. The copied
web files (`android/app/src/main/assets/public`, `ios/App/App/public`) are
gitignored and regenerated each time.

Icons and splash screens are generated from the one real logo by
`node scripts/build_brand_assets.mjs` (the same script as the favicons).

To point a test build at another server, put
`VITE_MOBILE_API_ORIGIN=https://your-server` in `frontend/.env.mobile`
(gitignored) and run `mobile:sync`. That server must allow the app's origins
(the backend does by default). Android blocks plain `http://` from the app,
so test against an HTTPS server, not a laptop's `http://192.168…`.

## Build requirements

| | Android | iOS |
|---|---|---|
| OS | Windows, macOS or Linux | **macOS only** |
| Tools | JDK 21, Android SDK 36 (Android Studio includes both) | Xcode 26+ (Capacitor 8), CocoaPods not needed (SPM) |
| Node | 22+ for the Capacitor CLI | 22+ |

The website's own build (Docker, CI) does not run the Capacitor CLI and is
unaffected by its Node 22 requirement.

## Testing on your phone

### Android

The published release installs from https://chineseverse.qobus.tj/download,
the same way learners get it. To test your own changes before publishing:

1. Build a debug APK: in `frontend/android/` run `gradlew assembleDebug`
   (or Android Studio → Run). Output: `android/app/build/outputs/apk/debug/app-debug.apk`.
2. Either connect the phone by USB with *Developer options → USB debugging* on
   and run `adb install -r app-debug.apk`, or copy the APK to the phone and
   open it (allow "install unknown apps" for your file manager).
3. Sign in with an existing ChineseVerse account (username + password).
   A debug build has a different signature from the published release, so
   uninstall one before installing the other.

A debug build can be inspected from desktop Chrome at `chrome://inspect`.

### iPhone

On a Mac with Xcode, open `ios/App/App.xcodeproj` (`npm run mobile:ios`),
choose your Apple ID team under *Signing & Capabilities*, plug in the iPhone
and press Run. A free Apple ID works for your own device (the install expires
after 7 days); TestFlight needs the paid Apple Developer Program.

### What to check on a real device

- [ ] Sign in, sign out, reopen the app (still signed in), reopen offline
      (still signed in, offline notice shown)
- [ ] Register a new account, onboarding, placement test (listening questions speak)
- [ ] Dashboard, HSK levels, lessons, vocabulary, Hanzi (stroke animation), grammar
- [ ] Practice and review rounds: graded answers, XP, companion reaction
- [ ] Every speaker button speaks Chinese; tap again stops it
- [ ] Mic answers (Voice Companion, practice): permission prompt, transcript
- [ ] Tone Coach recording and playback
- [ ] Duels, community, notifications, AI assistant (streamed reply)
- [ ] Settings: language switch (all four), Ink/Paper theme (status bar text follows),
      avatar upload from the gallery and camera
- [ ] Notch / Dynamic Island / gesture bar: nothing hidden under them, both orientations
- [ ] Android back button: back through pages, leaves on the first screen
- [ ] Airplane mode mid-lesson: a clear message, no crash, progress intact after reconnecting

## Publishing the downloadable APK

Visitors download the app from **https://chineseverse.qobus.tj/download**
(`src/pages/Download.jsx`, linked from the landing page). The APK is not in
this repository or the website build: it is an asset of a **GitHub Release**
on the public repo, so anyone can download it over HTTPS without signing in.

| | |
|---|---|
| Release | https://github.com/zargulak11-hash/Chineseverse/releases/tag/android-v1.0 |
| File the button downloads | `…/releases/download/android-v1.0/ChineseVerse-1.0-android.apk` |
| Always-newest alias | `…/releases/latest/download/ChineseVerse.apk` (same file, fixed name) |
| Signing certificate SHA-256 | `2c884436c263b8b522d2486d8e011f4665640bf0123b0aaa450e1f14de36d00d` |

**Signing.** Public builds are signed, non-debuggable **release** builds,
never the debug APK and never the unsigned AAB. The release key lives
outside the repository, in
`%LOCALAPPDATA%\ChineseVerseBuildTools\signing\` (`chineseverse-release.jks`
plus `keystore.properties` with its password). A copy of that
`keystore.properties` sits in `frontend/android/` (gitignored), which is
what makes `assembleRelease` sign. **Back both files up somewhere safe.**
Android only installs an update signed with the same key, so if the key is
lost, every learner has to uninstall and reinstall.

**Releasing a new version:**
1. Raise `versionCode` (by 1) and `versionName` in `frontend/android/app/build.gradle`.
2. `npm run mobile:sync`, then `cd frontend/android && gradlew --no-daemon assembleRelease`
   → `app/build/outputs/apk/release/app-release.apk`.
3. Verify before publishing: `apksigner verify --print-certs` shows the
   certificate above; `aapt2 dump badging` has no `application-debuggable`;
   install it over the previous version on a phone or emulator (an in-place
   update proves the key matches) and sign in.
4. Create release `android-v<version>` on GitHub (*Releases → Draft a new
   release*) and attach the APK twice: as `ChineseVerse-<version>-android.apk`
   and as `ChineseVerse.apk`. Mark it as the latest release.
5. Download it once without signing in and compare its SHA-256 with the
   built file.
6. Update the five values in `frontend/src/appDownload.js` (version,
   fileName, url, sizeBytes, sha256), commit and push; the website deploy
   switches the button over. Keep the previous release, since links to old
   versions keep working.

Debug builds are for development only: they are inspectable over USB and
signed with whichever PC built them. (An emulator image of type
`userdebug` makes *every* app's WebView inspectable, the release build
included. Real phones are `user` builds, and Capacitor keeps WebView
debugging off in release builds.)

## Releasing to Google Play

1. **Google Play developer account**, one-time US$25, opened by the owner
   (`play.google.com/console`). Not done.
2. **Signing key:** the release key above already exists, and
   `gradlew bundleRelease` signs the AAB with it
   (`app/build/outputs/bundle/release/app-release.aab`). When enrolling in
   **Play App Signing**, choose to *use your existing app signing key* and
   export this key with Play's PEPK tool. Then the Play version and the
   APK people already installed from the website share one signature, and
   updates install over each other. If Google generates a new key instead,
   website installs must be uninstalled before installing from Play.
3. In Play Console: create the app and upload the AAB to *Internal testing*
   first, then production.
4. Store listing: title, short and full description (EN / RU / TG / ZH),
   `store-assets/play-icon-512.png`, a 1024×500 feature graphic, and at
   least 2 phone screenshots.
5. **App content** forms: privacy policy URL, Data safety, ads (none),
   content rating questionnaire, target audience, and an **account deletion**
   URL (see blockers).
6. New personal developer accounts must run a **closed test with at least 12
   testers for 14 days** before production access is granted.

## Releasing to the Apple App Store

1. **Apple Developer Program**, US$99 per year, enrolled by the owner. Not done.
2. On a Mac: open the project, set the team, check *Signing & Capabilities*,
   bump the build number, *Product → Archive*, then *Distribute App* → App Store Connect.
3. In App Store Connect: create the app with bundle id `tj.qobus.chineseverse`,
   fill in the description and keywords per language, screenshots (6.9" and
   6.5" iPhone; iPad screenshots too, because the app runs on iPad), support URL,
   privacy policy URL, the **App Privacy** questionnaire and age rating.
4. Give the reviewer a working sign-in in *App Review Information*: a real
   account you create yourself for the review, not demo data in the database.
5. Export compliance: the app declares `ITSAppUsesNonExemptEncryption = false`
   (it only uses HTTPS).
6. Test through TestFlight before submitting.

## Blockers before either store will accept the app

These are product and legal work the owner has to decide on. None of them
are built yet:

1. **A privacy policy** at a public URL (both stores require one). It must
   cover what the backend stores: account email and username, password hash,
   learning progress and activity, uploaded profile photos, AI assistant
   conversations (sent to Google Gemini when enabled), community follows and
   duels, and notification emails. It must also say that speech recognition
   runs on the phone's own recognizer (Google or Apple), with only the text
   reaching ChineseVerse.
2. **In-app account deletion.** Apple guideline 5.1.1(v) and Google Play's
   data-deletion policy both require learners to be able to delete their own
   account (and Play also wants a web URL for it). Today only an admin can
   delete a user (Admin → Users). This needs a new, carefully reviewed
   `DELETE /api/me` that reuses `crud.delete_user_cascade_safe`.
3. **Data safety (Play) / App Privacy (Apple)** answers that match the policy above.
4. **Target audience.** If the app is aimed at children under 13, Google's
   Families policy and Apple's Kids category rules apply. Choose deliberately.
5. **Store copy, screenshots and the feature graphic.**

## Limitations

- **Google and GitHub sign-in are not available in the app yet.** Google
  blocks its sign-in inside embedded WebViews, and the GitHub flow returns to
  the website's address, so the buttons are hidden in the app.
  A learner who only ever signed in with Google has no password, so they
  can't sign in to the app until one of these is done:
  - native Google Sign-In (a Capacitor plugin plus Android and iOS OAuth
    clients in Google Cloud Console, with the Android client registered
    against the Play signing key's SHA-1). The backend already verifies
    Google ID tokens; the native client's token audience must match
    `GOOGLE_CLIENT_ID`, or the backend must accept the extra client ids;
  - or a "set a password" option for Google accounts.
  Adding Google sign-in on iOS also triggers Apple guideline 4.8, which
  requires offering **Sign in with Apple** too.
- **Text-to-speech voices** come from the phone. A phone with no Chinese voice
  installed stays silent, the same as a browser without one. On a fresh
  Android device the first Chinese phrase can fail silently while Google TTS
  downloads its Mandarin voice; the next tap works (seen on the emulator).
  Tajik has no voice on stock Android or iOS, so the assistant reads only the
  Chinese.
- **Older Android WebViews** (below Chromium 140, e.g. a stock Android 16
  emulator with WebView 133) can't draw under the status and gesture bars.
  Capacitor then pads the window, and the bars show the Ink background in
  both themes (`values/colors.xml`, `src/native.js`). Phones with an updated
  Android System WebView draw edge to edge and the bars follow the theme.
- **The 1024px App Store icon is upscaled** from the 565px emblem in the only
  logo file (`frontend/photo/`). A larger or vector master would make it sharper.
- **No push notifications.** Notifications stay in-app and by email.
- **Fonts** come from Google Fonts when online and fall back to the system UI
  font offline, as on the website.
