# ArcLibrary r22 — full catalog — iOS catalog plugin

This is a new iOS ARM64 library-management plugin integrated with the hash-guarded fix14 test host. It ports behavior from the user's Android `LibraryCatalog`, `ChartArchive`, `ChartFormat`, `ChartMetadata`, `PackCovers` and `ChartLibrary` implementations. It is not a generic injector for arbitrary Arcaea versions, and no Android APK is changed.

The previous iOS import action routes to `ArcLibrary.dylib`; its legacy `importArchive` entry returns failure immediately and is not used by the new plugin. Shared native resource redirection and engine-thread reload hooks remain in the host compatibility patch, alongside the preceding practice/lifecycle/partner fixes.

## Features

- Default import destination is the existing Arcaea/base pack. Existing Another songs migrate to base without changing their asset IDs, and the old Another pack definition is removed from the new catalog.
- ZIP/ARCPKG input, at most 128 entries, 128 MiB per entry, 256 MiB total, stored/deflated entries, local/central header consistency, CRC, unsafe-path and duplicate-basename checks.
- UTF-8 and UTF-16 text decoding, AFF header/separator/timing/parenthesis checks ported from Android, integer offset bounds. Normalize line endings before saving.
- Conventional jacket/audio names; songlist.json/songlist.txt/songlist/song.json/song.txt and JSON .arcproj metadata; direct song object, one-song wrapper or array. One song per archive. Metadata is optional, as on Android.
- Missing thumbnail is generated. Images are normalized to JPEG jackets and 256px previews; no music re-encoding. OGG signature and size are checked, not a full audio decode.
- Preserve available artist/designer information and unknown metadata. Background IDs must exist in the current game. Generate a separate local ID for each distinct import. Reject existing normalized AFF SHA256 content before preparing and again before committing; ZIP names and metadata IDs do not bypass this check. Only actual AFF difficulties are added; Beyond charts enable their local unlock.
- Song deletion/move; pack creation/detail/delete/move; category creation/delete; centered 403x717 cover crop/scale and native-resolution aliases; undo the latest catalog edit. Arcaea/base and its default category are retained as the required default destination.
- Deletion changes catalog records and retains resources for undo. It is not a permanent disk-cleaning operation. Refresh/open reads the active catalog files; there is no per-frame full catalog scan.
- Four-space songlist/packlist JSON. Custom categories are visible in the management page, and their native runtime packs map to Arcaea because the game's native category enum is fixed.
- A single atomic active.json swap activates fully written catalog generations. Failed transactions do not activate half-written lists. Canceled/uncommitted staging data is cleared when preparing the next import.

## Build

Prerequisites: Python 3.11+, Zig 0.15.2, Node.js for catalog tests; Unicorn and Pillow for native host tests (`requirements.txt`). Playwright with a locally installed browser is optional for responsive layout QA.

1. Obtain the original fix14 IPA. `patch_ios.py` requires the expected original main executable and plugin hashes; an already patched IPA is not accepted as input.
2. `python build_library.py --zig PATH_TO_ZIG`
3. `python patch_ios.py original.ipa r22-full.ipa --zig PATH_TO_ZIG`
4. Sign the complete app and both embedded dylibs with your own account. Keep the installed app's signing identity and bundle ID configuration to retain private data.

The Windows Zig Mach-O linker crashed during development. The reproducible build therefore compiles C objects only, then uses `link_library.py`, a restricted deterministic Mach-O linker supporting the audited relocation set. It emits explicit system-framework dependencies, dyld binding/rebase/export metadata and a symbol table/dynamic symbol table. Unknown relocations or imports are rejected. It does not supply an Apple SDK or a signing identity.

The standalone plugin ZIP contains the new dylib and UI assets without game fonts. The complete IPA already includes the fonts copied from its input game. The plugin ZIP requires this r22 host bridge and native main difficulty patch; dropping it into an unrelated app does not register the entry/reload hooks.

## Validation and limits

`node test_catalog.cjs` tests catalog operations and migration. `node test_ui.cjs` uses Playwright/Edge for five viewport sizes; set PLAYWRIGHT_MODULE if the module is outside the default search path. Official fonts are copied from the input game only for the IPA and local layout test, never exported in the source archive.

For ARM64 native tests, first extract the original game/plugin with `inspect_ipa.py` so `binaries/ArcaeaPractice.dylib` and `binaries/Arc-mobile` are available. The build generates diagnostics.o and the new dylib. Run `python test_library_native.py SAMPLE_ZIP` and `python test_library_link.py`, plus the retained window/run-loop/lifecycle/pause/entry/partner/Mach-O tests. `test_import_archive.py` is retained as the host Foundation/filesystem model dependency; its old-importer test main is obsolete for r12 and is not a new-importer test.

Native tests execute the newly compiled ARM64 parser, import preparation, image-rendering requests, catalog transaction and reload atomic. Foundation/filesystem/zlib/UIKit responses are host substitutes. Link tests inspect every emitted relocation and dyld stream. These do not execute iOS dyld, Sideloadly signing, the actual document picker/WKWebView, native game catalog parser bodies or gameplay. The target device remains the user's iPad Pro 2022 with iPadOS 27.0; physical acceptance is still required.

Private catalog files are under the existing app Library/ArcPracImports directory. The active generation contains ArcLibrary.json (authoritative manager catalog) and generated songs/songlist, songs/packlist and songs/unlocks. ArcLibrary-undo.json stores the prior catalog. Nothing is uploaded or sent over the network; the local UI uses a restrictive CSP and only displays metadata as text.

Source export contains only repair/plugin code and synthetic tests/verification. It contains no original game, fonts, sample ZIP, device recording/log, certificate, provisioning profile or signing key.


R14 corrects the system file-picker presentation selector (`presentViewController:animated:completion:`). The former `completionHandler:` spelling is a WebKit pattern and is not a UIViewController method. Both ZIP and pack-cover pickers use the corrected path. The supplied new device crash shows `doesNotRecognizeSelector:` followed by `ArcLibrary pick`; the host entry regression reproduces that failure in r13 and executes the corrected r14 path.

A retained single-picker guard prevents duplicate presentation, close/reload/refresh during a selection, and stale callbacks. Validate local NSURL results and treat empty selection as cancellation. Do not present while the app is inactive or the manager view is detached. Immediate main-thread cancellation/error notifications are separate from worker completion, so they cannot clear ownership of a newer operation. Close removes the WK message handler. Unsupported system presentation methods return a visible error instead of being invoked.

Run `python test_library_entries.py` for actual ARM64 window construction, selector routing, document delegate callbacks, background/presentation guards, empty/invalid/stale results, ZIP preparation, close/reopen and reload-request tests using modeled system frameworks. Its historical r13 reproduction needs the adjacent r13 build; the source export includes no previous proprietary binary. `node test_ui_entries.cjs` exercises the manager DOM actions with a simulated native bridge. `test_library_native.py SAMPLE_ZIP` additionally passes the original sample through production catalog.js and the native transaction, compares saved OGG bytes and normalized AFF, and checks the host active-generation reader. These tests do not execute Apple's UIKit, native game parser bodies, audio decoder or gameplay.

The r13 launch-alignment fix is retained: every LINKEDIT stream starts on an eight-byte boundary. `test_dyld_layout.py` verifies current alignment, bounds and no overlap; historical r12 reproduction needs that adjacent build. All recorded current tests are rerun for r14. No claim of full physical iPad validation is made.


R15 native difficulty-tab repair
-------------------------------
The selected Eternal and Beyond tab enabled states now permit another tap. The main tab callback requests the alternate class only when tapping the already-selected class 3 or 4; the ordinary first tap and Past/Present/Future routing are preserved. Before changing to class 3/4, a bounded native SongManager tree walk checks the parsed availability flags of real songs. Empty/missing/uninitialized targets leave the selection unchanged. The existing swap callback shares this guard. No disk scan is done per frame, and no missing AFF or difficulty entry is fabricated.

`patch_difficulty.py` accepts only the exact input main executable hash. It writes a small leaf stub into a verified zero-filled range of the existing executable RX segment, redirects two callbacks, and changes two selected-tab enabled states. It leaves executable size, load commands, segments, framework bindings and existing practice code intact. The complete app must be re-signed after changes. The original game executable is no longer byte-identical; release consistency checks verify that its five declared byte ranges are the only changes. This repair is specific to this fix14 iOS game layout.

Build packaging assembles `difficulty.s` and applies the main patch automatically. `python test_difficulty.py` executes the real main callbacks and availability accessor at three load bases, 2400 class/current/availability combinations, old wrong-class reproduction, tree successor traversal, empty catalogs, null state, invalid indices and cyclic-tree bounds. The native UI/filter rendering, real song parser bodies and gameplay remain outside the host model and require iPad acceptance. All retained regression suites are rerun for r15. Existing imported songs need no reimport; open the library and apply/reload if an earlier catalog has not yet been activated.


R16 instruction-abort repair and stricter loader test
---------------------------------------------------
R15 used file offset 0x1652000 as a branch destination, but __PRACCODE has different file and VM offsets after zero-filled __DATA. That address belongs to non-executable DATA at runtime. The supplied device report shows an instruction-abort permission fault exactly at image+0x1652000. The corrected island is stored at file+0x1652000 and branches to image+0x16AA000, inside RX __PRACCODE. This is an address-generation error in r15, not a reason to change the user's signing identity.

`test_difficulty.py` now loads each Mach-O segment at its actual VM address, zero-fills the virtual DATA tail and enforces initprot (TEXT/RX versus DATA/RW). It first reproduces r15's instruction fetch protection fault, then executes the corrected callbacks at three load bases. The previous flat-file emulator could not catch this mapping error and is no longer used by this test. Source packaging and IPA consistency checks compare the final patched main with the binary produced from these tested sources. R15 is superseded.

The visible switching area is the existing top-left difficulty tab: after selecting Eternal, another tap toggles to available Beyond; the reverse applies to Beyond. There is no separate new overlay button. Visibility and real gameplay still require device acceptance; the test does not render the native song-selection UI.


R17 repeated-switch and refresh-state repair
-------------------------------------------
Two changed booleans in r15/r16 did not cover other exits from the native difficulty UI updates. R17 wraps the complete Beyond and Eternal update functions, runs their original rendering, and then restores the visible/enabled alternative tab from the active global filter (or remembered higher-mode preference). Only one alternative tab occupies the original position. Native Node visibility and Widget enabled setters are used, without a UIKit overlay or per-frame disk/catalog scan.

Main tab routing recognizes both the selected row difficulty and the global difficulty filter. A row can be a fallback with another difficulty; a repeated tap must still toggle the active filter. Class 3/4 changes now invoke the original native list re-filter function with its force parameter set, instead of the original current-row activation path. On failure the remembered mode is restored; on success native click feedback is retained. Past/Present/Future keep their original handler. Missing target, empty catalogs, uninitialized update arguments and bounded catalog traversal are checked.

The new post-update wrappers and their trampolines use the original prologue instructions and preserve the ARM64 stack/callee-saved registers. Code remains at the corrected r16 executable VM address, distinct from its file offset. The permission-fault reproducer remains in the test.

`test_difficulty.py` includes real ARM64 wrapper and Node/Widget setter execution, simulated original-renderer outcomes, 100 consecutive toggles per scenario/load base, fallback-row/global-filter mismatch, failed native rebuild and click feedback. The original renderer and list-rebuild body are host substitutes, so these are state-flow and ABI tests, not native iPad filtering/gameplay acceptance. All retained import/practice/lifecycle/partner/layout/link regressions are rerun for r18. Already imported songs need no reimport.

## r18 duplicate imports and difficulty textures

- Compute SHA256 from actual AFF resources after UTF-8/UTF-16 decoding, BOM removal and CRLF/CR normalization. Filenames, ZIP compression, metadata IDs and jackets are excluded. No audio or image perceptual matching.
- Reject any incoming AFF whose normalized content is already active. Recheck immediately before catalog activation. Read actual installed resources rather than trusting imported hash metadata.
- Opening the library computes existing fingerprints. Active local entries with identical complete hash sets are merged, with the first retained and subsequent metadata archived under `practice_duplicate_archive`. Physical resources remain available; applying and reloading makes the cleaned catalog visible to the game. Existing nonidentical or partial sets are retained.
- The crash-site UI vector copy now skips null elements before append and `Ref::retain`, rather than globally ignoring invalid retain calls.
- After native difficulty refresh, bind the game's own class-3 BYD and class-4 ETR normal/selected textures. The actual selected row determines the displayed higher difficulty before falling back to the global filter or saved preference. The selected tab remains clickable for repeated switching.
- Host tests execute ARM64 SHA256 for boundary fixtures; hashes of AFF buffers larger than 4096 bytes are substituted with hashlib in the transaction harness. UIKit image drawing, C++ texture loading/string allocation and the game's complete list rebuild are modeled, not physical iPad execution. The null-row test executes the real retain instruction and loop, with only vector append substituted.

## r19 complete native difficulty presentation

r18 only rebound the button texture. Native early returns could leave the button opacity zero and the independent `diffLabel3_base`/`diffLabel4_base` number hidden, and could retain a different difficulty's choice. r19 restores the full presentation after native updates:

- When only BYD or only ETR exists on the actual song, show that class. When both exist, use the selected higher class or saved preference. With neither, retain an explicit unavailable mode for switching across the catalog.
- Rebind the exact class-specific official normal/selected resources, restore button opacity and the independent number root. Query the actual native difficulty object and call the game's level renderer, preserving rating/plus notation, outline and positioning.
- Hide the alternate number root together with its button. Missing charts show `--` with reduced opacity and correct class artwork; no difficulty record or AFF is invented.
- All changes remain in the fingerprint-locked existing executable RX island. No per-frame file scan, new UIKit overlay or catalog migration is introduced by this rendering fix.

The new `test_presentation.py` reproduces the r18 omitted-opacity/hidden-level failure, exercises 1920 class/mode states at three load bases, and repeats 100 row/mode changes per base. It executes the native difficulty accessor and native level-render control flow; Cocos text/font rasterization, number-to-string formatting, scene lookup and texture loading remain host substitutes. Actual iPad acceptance is still required. For the historical reproduction fixture, compile `previous_difficulty_r18.s` with `zig cc -target aarch64-ios -c previous_difficulty_r18.s -o previous_difficulty_r18.o` before running that test. The unchanged ArcLibrary binary retains the r18 importer/hash regression record, whose SHA256 is checked against the packaged dylib.

## r20 ZIP background import

Metadata `bg` / `bg_inverse` at song level and on actual AFF difficulties now resolves against installed backgrounds first. When absent, a matching `<id>.jpg`, `.png`, `.jpeg` or `1080_<id>` image in the ZIP is validated and staged with the song. Nested archive directories use the existing safe basename normalization. Unreferenced jackets/previews are not treated as backgrounds.

The confirmation dialog shows the number of new backgrounds. Only successful import submission publishes normalized 1920x1080 JPEG backgrounds under the private library's `img/bg/1080/<id>.jpg` and `img/bg/<id>.jpg` aliases. Cover scaling uses center fill; background normalization also uses center fill. Bundled and existing private background IDs are reused without replacement. A missing, corrupt, oversized or unsafe referenced background is an error. Inactive placeholder difficulties do not cause irrelevant background errors.

The retained host's existing C++ fullPath resource resolver now accepts `img/bg/` as well as `songs/`, retaining its traversal and existence checks and bundled fallback. The original r19 difficulty/pause behavior is unchanged. Backgrounds are shared retained resources, including after song deletion or undo, consistent with song resources. Failed catalog activation may leave unreferenced generation/resource files but never switches the active song list; the canonical 1080 background alias is written last so an interrupted alias write can be retried.

`test_backgrounds.py SAMPLE.zip` executes the compiled importer, background transaction, cold read and actual retained fullPath control flow, with Foundation/filesystem/UIKit rendering and C++ output construction modeled. It covers built-in priority, existing background reuse, PNG/JPEG inputs, inverse/difficulty backgrounds, missing/corrupt/oversized images, path rejection, failed writes and retry, and the supplied RoquiRa package. This does not replace physical iPad rendering/playback verification. The unchanged r19 main binary is checked against its native presentation tests; the ArcLibrary binary is newly built and importer regressions rerun in r20.

## r21 native background canvas and existing-image repair

The bundled game's background JPGs and supplied source are 1920x1440. r20 incorrectly cropped new backgrounds to 1920x1080, which left uncovered space in the native scene. r21 uses the native 1920x1440 canvas. A valid source JPEG already at that size is retained byte for byte; other image sizes are center-filled to the native canvas.

Opening/refreshing the library scans private backgrounds on the worker queue. Old 1920x1080 private files are backed up under `background-backup-r20` and normalized once, without touching bundled backgrounds or the active song catalog. This removes missing canvas coverage but cannot recover pixels already cropped by r20. To restore those pixels, select the original ZIP again: if the AFF already exists and it supplies a recoverable old background, the plugin offers a background-only repair instead of adding another song. Original source bytes replace only eligible backed-up private backgrounds; a marker prevents repeated repairs. This action keeps the active song list, identifiers, packs and score references unchanged. Existing normal imports remain content-deduplicated.

`test_bg_dimensions.py` executes compiled 4:3 preservation, legacy normalization/idempotence, backups, staged background-only restore, expired stage rejection, write-failure retry, builtin exclusion and unchanged catalog checks. `test_ui_entries.cjs` checks the new confirmation and its dedicated bridge action. Actual fullscreen presentation still requires iPad verification; host framework/rasterization limits remain as described above.

## r22 full catalog release

Build without `--sayonara-only` to retain all 562 original bundled songs, 63 pack definitions and every original `songs/` archive entry unchanged. No externally supplied test-song ZIP is included. Practice/lifecycle/partner/difficulty/background behavior is retained and regression checked.

The full release includes an opt-in marker. On opening the library after overwriting a single-song installation, the compiled loader backs up its old master, adds missing bundled songs/packs, preserves imported IDs/resources and existing pack edits, and assigns unique presentation indexes. The UI activates the restored catalog through the existing atomic commit. Apply and reload once; a private completion marker means later user deletions are respected rather than repeatedly restored. This synchronization does not scan all bundled AFF files on each refresh; snapshot hashes are computed for local import records, while import validation still compares actual installed AFF content.

The native game's reserved `single` group (Memory Archive, 134 songs) does not occur in its packlist. Management represents it with one virtual entry and the existing bundled cover; runtime serialization excludes that entry so native special handling and the original 63-pack list remain intact. `test_full_catalog.py` exercises the compiled merge and activation plus production JS against the actual original catalog. Final archive checks require all original song/pack files and catalog bytes to match input CRC/size and data. Physical iOS launch/gameplay is not available on this host.

## Source export setup

Use the root BUILDING.md and tools/check.py for the standalone ios branch. The full-catalog build omits --sayonara-only. That flag is retained only for optional single-song diagnostic builds. Historical r12/r13 binary reproducers are optional; the exported current-version checks do not require those old builds. Existing verification JSON records describe the original release run; verification/export-checks.json describes this export.
