.text
.p2align 2
.globl _bootstrap
_bootstrap:
 stp x29, x30, [sp, #-32]!
 stp x20, x19, [sp, #16]
 bl _original_init
 mov w19, w0
 bl _restore_partner
 adr x0, ready
 cbnz w19, 1f
 adr x0, failed
1:
 adr x1, boot_file
 bl report
 mov w0, w19
 ldp x20, x19, [sp, #16]
 ldp x29, x30, [sp], #32
 ret
.globl _common_mode
_common_mode:
 adr x9, common_mode_address
 ldr x0, [x9]
 ldr x0, [x0]
 ret
.globl _ui_started
_ui_started:
 stp x29, x30, [sp, #-32]!
 stp x20, x19, [sp, #16]
 bl _objc_autoreleasePoolPush
 mov x19, x0
 adr x0, ui_entered
 adr x1, ui_file
 bl report
 mov x0, x19
 ldp x20, x19, [sp, #16]
 ldp x29, x30, [sp], #32
 ret
.globl _ui_registered
_ui_registered:
 stp x29, x30, [sp, #-32]!
 stp x20, x19, [sp, #16]
 mov x19, x0
 mov x20, x2
 bl _objc_msgSend
 adr x0, ui_registered
 cbnz x19, 1f
 adr x0, ui_no_displaylink
 b 2f
1:
 cbnz x20, 2f
 adr x0, ui_no_runloop
2:
 adr x1, ui_file
 bl report
 ldp x20, x19, [sp, #16]
 ldp x29, x30, [sp], #32
 ret
.globl _tick_probe
_tick_probe:
 stp x29, x30, [sp, #-32]!
 stp x20, x19, [sp, #16]
 mov x19, x0
 cmp x0, #0
 cset w20, ne
 add w20, w20, #1
 adr x9, last_stage
 ldr w8, [x9]
 cmp w8, w20
 b.eq 2f
 str w20, [x9]
 adr x0, window_missing
 cbz x19, 1f
 adr x0, window_found
1:
 adr x1, window_file
 bl report
2:
 mov x0, x19
 ldp x20, x19, [sp, #16]
 ldp x29, x30, [sp], #32
 cbnz x0, 1f
 b _tick_nil
1:
 ret
// Unlike the original CBZ, the BL probe has already set LR to tick+0x38.
// The nil branch goes directly to tick's original epilogue.
report:
 stp x29, x30, [sp, #-64]!
 stp x20, x19, [sp, #16]
 stp x22, x21, [sp, #32]
 stp x24, x23, [sp, #48]
 mov x19, x0
 mov x20, x1
 bl _objc_autoreleasePoolPush
 mov x21, x0
 adr x0, file_manager
 bl _objc_getClass
 mov x22, x0
 adr x0, default_manager
 bl _sel_registerName
 mov x1, x0
 mov x0, x22
 bl _objc_msgSend
 mov x22, x0
 adr x0, urls_for_directory
 bl _sel_registerName
 mov x1, x0
 mov x0, x22
 mov w2, #9
 mov w3, #1
 bl _objc_msgSend
 mov x22, x0
 adr x0, object_at_index
 bl _sel_registerName
 mov x1, x0
 mov x0, x22
 mov x2, #0
 bl _objc_msgSend
 mov x22, x0
 adr x0, path
 bl _sel_registerName
 mov x1, x0
 mov x0, x22
 bl _objc_msgSend
 mov x22, x0
 adr x0, string_class
 bl _objc_getClass
 mov x23, x0
 adr x0, string_from_utf8
 bl _sel_registerName
 mov x24, x0
 mov x1, x24
 mov x0, x23
 mov x2, x20
 bl _objc_msgSend
 mov x20, x0
 adr x0, append_component
 bl _sel_registerName
 mov x1, x0
 mov x0, x22
 mov x2, x20
 bl _objc_msgSend
 mov x22, x0
 cbz x22, 3f
 mov x0, x23
 mov x1, x24
 mov x2, x19
 bl _objc_msgSend
 mov x20, x0
 adr x0, write_string
 bl _sel_registerName
 mov x1, x0
 mov x0, x20
 mov x2, x22
 mov w3, #1
 mov w4, #4
 mov x5, #0
 bl _objc_msgSend
3:
 mov x0, x21
 bl _objc_autoreleasePoolPop
 ldp x24, x23, [sp, #48]
 ldp x22, x21, [sp, #32]
 ldp x20, x19, [sp, #16]
 ldp x29, x30, [sp], #64
 ret
file_manager: .asciz "NSFileManager"
default_manager: .asciz "defaultManager"
urls_for_directory: .asciz "URLsForDirectory:inDomains:"
object_at_index: .asciz "objectAtIndex:"
path: .asciz "path"
string_class: .asciz "NSString"
string_from_utf8: .asciz "stringWithUTF8String:"
append_component: .asciz "stringByAppendingPathComponent:"
write_string: .asciz "writeToFile:atomically:encoding:error:"
boot_file: .asciz "ArcPrac-startup.txt"
window_file: .asciz "ArcPrac-window.txt"
ui_file: .asciz "ArcPrac-ui.txt"
ready: .asciz "windowfix-r22: dylib constructor executed; native initialization returned success.\n"
failed: .asciz "windowfix-r22: dylib constructor executed; native initialization returned failure.\n"
window_missing: .asciz "windowfix-r22: display-link tick executed; no eligible game window found yet.\n"
window_found: .asciz "windowfix-r22: display-link tick executed; game window found.\n"
ui_entered: .asciz "windowfix-r22: main-queue UI initialization block entered.\n"
ui_registered: .asciz "windowfix-r22: display link registered with main run loop and system common-modes constant.\n"
ui_no_displaylink: .asciz "windowfix-r22: UI initialization ran but CADisplayLink is nil.\n"
ui_no_runloop: .asciz "windowfix-r22: UI initialization ran but main NSRunLoop is nil.\n"
// PC-relative load of mutable data is redirected by the linker helper.
.p2align 2
.globl _last_stage_address
last_stage:
_last_stage_address: .long 0
.p2align 3
.globl _common_mode_data_address
common_mode_address:
_common_mode_data_address: .quad 0

// r3: notifications only detach UIKit and publish a cancellation request.
// FMOD, scene rebuilds, and practice cancellation run on the engine thread.
.p2align 2
.globl _register_tick
_register_tick:
 stp x29,x30,[sp,#-32]!
 stp x20,x19,[sp,#16]
 mov x19,x0
 bl _class_addMethod
 mov x20,x0
 adr x0,resign_selector
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 adr x2,_resign
 adr x3,method_type
 bl _class_addMethod
 adr x0,active_selector
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 adr x2,_active
 adr x3,method_type
 bl _class_addMethod
 mov x0,x20
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#32
 ret
.globl _install_observers
_install_observers:
 stp x29,x30,[sp,#-48]!
 stp x20,x19,[sp,#16]
 stp x22,x21,[sp,#32]
 str x0,[x22,#0x88] // original displaced instruction
 mov x19,x0
 adr x0,notification_center
 bl _objc_getClass
 mov x20,x0
 adr x0,default_center
 bl _sel_registerName
 mov x1,x0
 mov x0,x20
 bl _objc_msgSend
 mov x20,x0
 adr x0,resign_selector
 bl _sel_registerName
 mov x21,x0
 adr x0,will_resign
 bl nsstring
 mov x22,x0
 bl add_observer
 adr x0,did_background
 bl nsstring
 mov x22,x0
 bl add_observer
 adr x0,active_selector
 bl _sel_registerName
 mov x21,x0
 adr x0,did_active
 bl nsstring
 mov x22,x0
 bl add_observer
 mov x0,x19
 ldp x22,x21,[sp,#32]
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#48
 ret
add_observer:
 stp x29,x30,[sp,#-16]!
 adr x0,add_observer_selector
 bl _sel_registerName
 mov x1,x0
 mov x0,x20
 mov x2,x19
 mov x3,x21
 mov x4,x22
 mov x5,#0
 bl _objc_msgSend
 ldp x29,x30,[sp],#16
 ret
.globl _resign
_resign:
 stp x29,x30,[sp,#-32]!
 stp x20,x19,[sp,#16]
 adr x19,state_address
 mov w8,#1
 add x9,x19,#16
 stlr w8,[x9]
 adr x20,plugin_data_address
 ldr w8,[x20,#0x120]
 cbz w8,1f
 add x9,x19,#20
 stlr w8,[x9]
1:
 // Invalidate queued preview callbacks; a detached panel cannot swallow input.
 str wzr,[x20,#0x120]
 strb wzr,[x20,#0x208]
 strb wzr,[x20,#0x98]
 ldr x0,[x20,#0x90]
 str xzr,[x20,#0x90]
 cbz x0,2f
 mov x19,x0
 str xzr,[x20,#0x1f0]
 adr x0,end_editing
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 mov w2,#1
 bl _objc_msgSend
 adr x0,remove_superview
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 bl _objc_msgSend
2:
 ldr x19,[x20,#0x1d0]
 cbz x19,3f
 adr x0,set_hidden
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 mov w2,#1
 bl _objc_msgSend
3:
 bl _persist_partner
 adr x0,suspended_message
 adr x1,lifecycle_file
 bl report
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#32
 ret
.globl _active
_active:
 adr x9,state_address
 add x9,x9,#16
 stlr wzr,[x9]
 ret
.globl _ui_tick_gate
_ui_tick_gate:
 adr x9,state_address
 add x9,x9,#16
 ldar w8,[x9]
 cbnz w8,1f
 stp x29,x30,[sp,#-48]!
 stp x0,x1,[sp,#16]
 str x2,[sp,#32]
 bl _persist_partner
 ldp x0,x1,[sp,#16]
 ldr x2,[sp,#32]
 ldp x29,x30,[sp],#48
 sub sp,sp,#0x80
 b _tick_body
1:
 ret
.globl _engine_gate
_engine_gate:
 adr x9,state_address
 add x10,x9,#16
 ldar w8,[x10]
 cbnz w8,2f
 stp x29,x30,[sp,#-32]!
 str x0,[sp,#16]
 bl _audio_ready
 mov w11,w0
 ldr x0,[sp,#16]
 ldp x29,x30,[sp],#32
 cbz w11,2f
 stp x29,x30,[sp,#-32]!
 str x0,[sp,#16]
 bl _library_poll
 ldr x0,[sp,#16]
 ldp x29,x30,[sp],#32
 adr x9,state_address
 add x9,x9,#20
 ldar w8,[x9]
 cbz w8,1f
 stlr wzr,[x9]
 stp x29,x30,[sp,#-32]!
 str x0,[sp,#16]
 mov w0,w8
 bl _practice_cancel
 ldr x0,[sp,#16]
 ldp x29,x30,[sp],#32
1:
 sub sp,sp,#0xb0
 b _engine_body
2:
 adr x9,plugin_data_address
 ldr x9,[x9,#0x2c8]
 br x9
// Successful partner application publishes an index; it never calls Foundation.
.globl _partner_applied
_partner_applied:
 stlr w19,[x8]
 adr x9,state_address
 str w19,[x9,#32]
 mov w10,#1
 add x9,x9,#28
 stlr w10,[x9]
 ret
// The original consumes queued choices even before the user-data owner exists.
// Requeue until it is ready, which is essential during cold-start restoration.
.globl _partner_retry
_partner_retry:
 cmp w19,#0x80
 b.hi 1f
 adr x8,plugin_data_address
 add x8,x8,#0x38
 stlr w19,[x8]
1:
 adr x8,plugin_data_address
 b _partner_not_ready
.globl _restore_partner
_restore_partner:
 stp x29,x30,[sp,#-48]!
 stp x20,x19,[sp,#16]
 stp x22,x21,[sp,#32]
 bl _objc_autoreleasePoolPush
 mov x22,x0
 bl preferences
 mov x19,x0
 adr x0,partner_key
 bl nsstring
 mov x20,x0
 adr x0,object_for_key
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 mov x2,x20
 bl _objc_msgSend
 cbz x0,1f
 mov x21,x0
 adr x0,integer_value
 bl _sel_registerName
 mov x1,x0
 mov x0,x21
 bl _objc_msgSend
 cmp x0,#0x80
 b.hi 1f
 bl _partner_choose
1:
 mov x0,x22
 bl _objc_autoreleasePoolPop
 ldp x22,x21,[sp,#32]
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#48
 ret
.globl _persist_partner
_persist_partner:
 adr x9,state_address
 add x10,x9,#28
 ldar w8,[x10]
 cbz w8,2f
 stp x29,x30,[sp,#-48]!
 stp x20,x19,[sp,#16]
 stp x22,x21,[sp,#32]
 // Clear before reading latest index. Concurrent native publication sets dirty
 // again, guaranteeing a later tick persists the newest selection as well.
 stlr wzr,[x10]
 ldr w19,[x9,#32]
 cmp w19,#0x80
 b.hi 1f
 bl preferences
 mov x20,x0
 adr x0,partner_key
 bl nsstring
 mov x21,x0
 adr x0,set_integer
 bl _sel_registerName
 mov x1,x0
 mov x0,x20
 mov x2,x19
 mov x3,x21
 bl _objc_msgSend
1:
 ldp x22,x21,[sp,#32]
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#48
2:
 ret
preferences:
 stp x29,x30,[sp,#-32]!
 str x19,[sp,#16]
 adr x0,defaults_class
 bl _objc_getClass
 mov x19,x0
 adr x0,standard_defaults
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 bl _objc_msgSend
 ldr x19,[sp,#16]
 ldp x29,x30,[sp],#32
 ret
nsstring:
 stp x29,x30,[sp,#-32]!
 stp x20,x19,[sp,#16]
 mov x19,x0
 adr x0,string_class
 bl _objc_getClass
 mov x20,x0
 adr x0,string_from_utf8
 bl _sel_registerName
 mov x1,x0
 mov x0,x20
 mov x2,x19
 bl _objc_msgSend
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#32
 ret
notification_center: .asciz "NSNotificationCenter"
default_center: .asciz "defaultCenter"
add_observer_selector: .asciz "addObserver:selector:name:object:"
resign_selector: .asciz "arcpracWillResign:"
active_selector: .asciz "arcpracDidBecomeActive:"
method_type: .asciz "v@:@"
will_resign: .asciz "UIApplicationWillResignActiveNotification"
did_background: .asciz "UIApplicationDidEnterBackgroundNotification"
did_active: .asciz "UIApplicationDidBecomeActiveNotification"
end_editing: .asciz "endEditing:"
remove_superview: .asciz "removeFromSuperview"
set_hidden: .asciz "setHidden:"
defaults_class: .asciz "NSUserDefaults"
standard_defaults: .asciz "standardUserDefaults"
partner_key: .asciz "ArcPrac.selectedPartner.v1"
object_for_key: .asciz "objectForKey:"
integer_value: .asciz "integerValue"
set_integer: .asciz "setInteger:forKey:"
lifecycle_file: .asciz "ArcPrac-lifecycle.txt"
suspended_message: .asciz "windowfix-r22: inactive; practice panel detached; cancellation deferred to foreground engine frame.\n"
.p2align 3
.globl _state_address
state_address:
_state_address: .quad 0

.p2align 3
.globl _plugin_data_address
plugin_data_address:
_plugin_data_address: .quad 0
// Main-thread snapshot polling must never spin while an engine thread is
// suspended. Keep the last complete UI snapshot if the shared lock is busy.
.p2align 2
.globl _state_try_read
_state_try_read:
 adr x9,plugin_data_address
 add x9,x9,#0x230
 ldaxrb w8,[x9]
 cbnz w8,1f
 mov w8,#1
 stxrb w10,w8,[x9]
 cbnz w10,1f
 add x10,x9,#4
 ldp q0,q1,[x10]
 ldp q2,q3,[x10,#32]
 stp q0,q1,[x0]
 stp q2,q3,[x0,#32]
 str wzr,[x10,#0x24]
 stlrb wzr,[x9]
 ret
1:
 clrex
 ret

// Never issue plugin seek/cancel/rebuild while the native mixer is suspended.
// The game's normal loop must run first, so its own backend update can resume
// the mixer (8e4d20 -> 10adff4 -> active byte at backend+0x10).
.p2align 2
.globl _audio_ready
_audio_ready:
 adr x9,plugin_data_address
 ldr x9,[x9,#0x278]
 cbz x9,2f
 mov w10,#0x81d8
 movk w10,#0x167,lsl #16
 ldr x10,[x9,x10]
 cbz x10,2f
 ldr x10,[x10,#0x10]
 cbz x10,2f
 ldr x10,[x10,#0x280]
 cbz x10,2f
 // Validate the exact FMOD backend before reading its private status bytes.
 mov w11,#0xb930
 movk w11,#0x14b,lsl #16
 add x11,x9,x11
 ldr x12,[x10]
 cmp x11,x12
 b.ne 1f
 ldrb w11,[x10,#0xa8]
 cbnz w11,1f
 ldrb w11,[x10,#0xc8]
 cbnz w11,1f
 ldrb w11,[x10,#0x10]
 cmp w11,#1
 cset w0,eq
 ret
1:
 mov w0,#0
 ret
2:
 // No initialized audio backend yet: permit normal plugin initialization.
 mov w0,#1
 ret

// x0 = GameScene. The game adds the pause menu to its HUD on show and removes
// it on hide; its local visible/running bytes can stay true after detachment.
// Use getParent (vtable+0x240), exactly as native show/hide at bb0930/bb0ae4.
.globl _scene_has_pause
_scene_has_pause:
 cbz x0,9f
 ldrb w8,[x0,#0x470]
 cbz w8,9f
 ldr w8,[x0,#0x2d0]
 cbnz w8,9f
 ldr x8,[x0,#0x2c8]
 cbnz x8,9f
 stp x29,x30,[sp,#-48]!
 stp x20,x19,[sp,#16]
 stp x22,x21,[sp,#32]
 mov x19,x0
 ldr x20,[x0,#0x380]
 cbz x20,8f
 ldr x21,[x20,#0x2c0]
 cbz x21,8f
 ldrb w8,[x21,#0x1c1]
 cbz w8,8f
 ldrb w8,[x21,#0x1d1]
 cbz w8,8f
 mov x0,x21
 ldr x8,[x0]
 ldr x8,[x8,#0x240]
 blr x8
 cmp x0,x20
 b.ne 8f
 // The HUD must itself still belong to the current scene. Walk at most 16
 // parents, rejecting hidden/detached ancestors and cycles by the bound.
 mov x21,x20
 mov w22,#16
1:
 cbz x21,8f
 cmp x21,x19
 b.eq 7f
 ldrb w8,[x21,#0x1c1]
 cbz w8,8f
 mov x0,x21
 ldr x8,[x0]
 ldr x8,[x8,#0x240]
 blr x8
 mov x21,x0
 subs w22,w22,#1
 b.ne 1b
 b 8f
7:
 ldrb w8,[x19,#0x1c1]
 cbz w8,8f
 ldrb w8,[x19,#0x1d1]
 cbz w8,8f
 mov w0,#1
 b 6f
8:
 mov w0,#0
6:
 ldp x22,x21,[sp,#32]
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#48
 ret
9:
 mov w0,#0
 ret
.globl _entry_allowed
_entry_allowed:
 adr x9,state_address
 add x9,x9,#16
 ldar w8,[x9]
 cbnz w8,9f
 stp x29,x30,[sp,#-16]!
 bl _audio_ready
 cbz w0,8f
 bl _running_scene
 cbz x0,8f
 adr x9,plugin_data_address
 ldr x9,[x9,#0x278]
 mov w10,#0x1dc0
 movk w10,#0x152,lsl #16
 add x9,x9,x10
 ldr x10,[x0]
 cmp x9,x10
 b.ne 8f
 bl _scene_has_pause
 ldp x29,x30,[sp],#16
 ret
8:
 mov w0,#0
 ldp x29,x30,[sp],#16
 ret
9:
 mov w0,#0
 ret
.globl _snapshot_pause_gate
_snapshot_pause_gate:
 stp x29,x30,[sp,#-16]!
 mov x0,x22
 bl _scene_has_pause
 mov w8,w0
 ldp x29,x30,[sp],#16
 cbnz w8,1f
 b _normal_kind
1:
 b _paused_kind
.globl _action_pause_gate
_action_pause_gate:
 cbnz x8,1f
 stp x29,x30,[sp,#-16]!
 bl _entry_allowed
 mov w8,w0
 ldp x29,x30,[sp],#16
 cbz w8,1f
 b _action_continue
1:
 b _action_denied
.globl _fresh_ui_kind
_fresh_ui_kind:
 stp x29,x30,[sp,#-16]!
 bl _entry_allowed
 add w8,w0,#1
 ldp x29,x30,[sp],#16
 ret

.p2align 2
.globl _hide_partner_lock
_hide_partner_lock:
 stp x29,x30,[sp,#-32]!
 str x19,[sp,#16]
 mov x19,x0
 // Original native-frame operation: hide lock. Also zero its own opacity,
 // because the native card's state update can set visible=true later that frame.
 blr x8
 ldr x8,[x19]
 ldr x8,[x8,#0x470]
 mov x0,x19
 mov w1,#0
 blr x8
 ldr x19,[sp,#16]
 ldp x29,x30,[sp],#32
 ret
.globl _offline_frame_refresh
_offline_frame_refresh:
 stp x29,x30,[sp,#-16]!
 // Restore a queued choice as soon as the native owner exists, including
 // StartScene before MainMenuScene builds its first portrait and UserCell.
 // The original frame function validates manager/owner readiness and our retry
 // hook retains the pending selection while either is unavailable.
 adr x9,plugin_data_address
 add x9,x9,#0x38
 ldar w8,[x9]
 cmp w8,#0x80
 b.hi 1f
 mov w1,#1
1:
 bl _offline_frame
 bl _refresh_partner_views
 ldp x29,x30,[sp],#16
 ret
.globl _refresh_partner_views
_refresh_partner_views:
 stp x29,x30,[sp,#-112]!
 stp x20,x19,[sp,#16]
 stp x22,x21,[sp,#32]
 stp x24,x23,[sp,#48]
 stp x26,x25,[sp,#64]
 stp x28,x27,[sp,#80]
 sub sp,sp,#0x800
 adr x27,plugin_data_address
 ldr x19,[x27,#0x278]
 cbz x19,9f
 bl _running_scene
 cbz x0,9f
 mov w9,#0xdfd8
 movk w9,#0x147,lsl #16
 add x9,x19,x9
 ldr x8,[x0]
 cmp x8,x9
 b.ne 9f
 mov x21,x0
 ldrb w8,[x21,#0x1c1]
 cbz w8,9f
 ldrb w8,[x21,#0x1d1]
 cbz w8,9f
 ldr x8,[x21,#0x2f0]
 cbz x8,9f
 ldr x20,[x27,#0x808]
 cbz x20,9f
 add x8,x27,#0x3c
 ldar w22,[x8]
 cmp w22,#0x80
 b.hi 9f
 // Include c9/ca explicitly: the two form flags straddle this halfword.
 ldrb w8,[x20,#0xc9]
 ldrb w9,[x20,#0xca]
 orr w23,w8,w9,lsl #8
 adr x28,state_address
 ldr x8,[x28,#40]
 cmp x8,x21
 b.ne 1f
 ldr x8,[x28,#48]
 cmp x8,x20
 b.ne 1f
 ldr w8,[x28,#56]
 cmp w8,w22
 b.ne 1f
 ldr w8,[x28,#64]
 cmp w8,w23
 b.eq 9f
1:
 // Skip the native fade/rebuild when its existing portrait already represents
 // this selection. On a form change in the same scene, a rebuild is required.
 mov w26,#1
 ldr x8,[x28,#40]
 cmp x8,x21
 b.ne 6f
 ldr w8,[x28,#64]
 cmp w8,w23
 b.ne 7f
6:
 ldr w8,[x21,#0x338]
 ldr w9,[x20,#0xc]
 cmp w8,w9
 b.ne 7f
 ldr x8,[x21,#0x300]
 cbz x8,7f
 ldr x8,[x21,#0x308]
 cbz x8,7f
 mov w26,#0
7:
 str x21,[x28,#40]
 str x20,[x28,#48]
 str w22,[x28,#56]
 str w23,[x28,#64]
 cbz w26,8f
 // Use the same native portrait builder as MainMenuScene::updateCharacter.
 mov w8,#0x6020
 movk w8,#6,lsl #16
 add x8,x19,x8
 mov x0,x21
 blr x8
8:
 // Refresh only self-profile UserCells. Other users' models remain untouched.
 mov w22,#1
 mov w23,#0
 str x21,[sp]
2:
 cbz w22,9f
 cmp w23,#2048
 b.hs 9f
 add w23,w23,#1
 sub w22,w22,#1
 ldr x21,[sp,x22,lsl #3]
 cbz x21,2b
 tst x21,#7
 b.ne 2b
 ldrb w8,[x21,#0x1c1]
 cbz w8,2b
 ldrb w8,[x21,#0x1d1]
 cbz w8,2b
 ldr x8,[x21]
 mov w9,#0x6080
 movk w9,#0x147,lsl #16
 add x9,x19,x9
 cmp x8,x9
 b.ne 4f
 ldr x1,[x21,#0x408]
 cbz x1,4f
 ldrb w8,[x1,#0x109]
 cbz w8,4f
 ldr w4,[x20,#0xc]
 ldr w8,[x1,#0x40]
 cmp w8,w4
 b.ne 3f
 ldrb w8,[x1,#0xb8]
 ldrb w9,[x1,#0xb9]
 orr w8,w8,w9,lsl #8
 ldrb w9,[x20,#0xc9]
 ldrb w10,[x20,#0xca]
 orr w9,w9,w10,lsl #8
 cmp w8,w9
 b.eq 4f
3:
 str w4,[x1,#0x40]
 ldrb w8,[x20,#0xc9]
 ldrb w9,[x20,#0xca]
 strb w8,[x1,#0xb8]
 strb w9,[x1,#0xb9]
 ldrb w2,[x21,#0x52a]
 mov w3,#0
 mov x0,x21
 mov w8,#0x303c
 movk w8,#2,lsl #16
 add x8,x19,x8
 blr x8
4:
 ldr x8,[x21,#0x140]
 cbz x8,2b
 tst x8,#7
 b.ne 2b
 ldp x24,x25,[x8]
 cmp x25,x24
 b.lo 2b
 sub x8,x25,x24
 cmp x8,#0x8000
 b.hi 2b
 tst x8,#7
 b.ne 2b
 cbz x24,2b
5:
 cmp x24,x25
 b.hs 2b
 cmp w22,#256
 b.hs 2b
 ldr x8,[x24],#8
 str x8,[sp,x22,lsl #3]
 add w22,w22,#1
 b 5b
9:
 add sp,sp,#0x800
 ldp x28,x27,[sp,#80]
 ldp x26,x25,[sp,#64]
 ldp x24,x23,[sp,#48]
 ldp x22,x21,[sp,#32]
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#112
 ret
.p2align 2
.globl _panel_pending_kind
_panel_pending_kind:
 // Begin deliberately hides the native pause node. Keep the UIKit panel while
 // the published active request matches this panel; do not require that hidden
 // node to remain visible. The caller already checks the completion ID first.
 adr x9,plugin_data_address
 ldr w8,[x9,#0xd8]
 and w10,w8,#0xfffffffe
 cmp w10,#2
 b.eq 1f
 ldr w10,[x9,#0x120]
 cbz w10,2f
 ldr w11,[x9,#0x100]
 cmp w10,w11
 b.ne 2f
 mov w8,#3
 ret
2:
 stp x29,x30,[sp,#-16]!
 bl _entry_allowed
 cmp w0,#0
 mov w8,#1
 cinc w8,w8,ne
 ldp x29,x30,[sp],#16
1:
 ret
.globl _native_begin_gate
_native_begin_gate:
 adr x9,plugin_data_address
 ldrb w8,[x9,#0x3dc]
 cbz w8,2f
 stp x29,x30,[sp,#-16]!
 mov x0,x20
 bl _scene_has_pause
 mov w8,w0
 ldp x29,x30,[sp],#16
 cbz w8,2f
 b _native_begin_body
2:
 // Replay the original load and keep all existing preview/apply/cancel paths.
 ldr x8,[x24,#0x278]
 b _native_begin_original

// The original overlay only knows the legacy partner button, which the tick
// permanently hides. The actual import UI has its own button and modal tree.
// Include its hit regions before falling back to the practice/partner regions.
.p2align 2
.globl _overlay_inside
_overlay_inside:
 stp x29,x30,[sp,#-64]!
 stp x0,x1,[sp,#16]
 stp x2,x3,[sp,#32]
 stp d0,d1,[sp,#48]
 bl _import_inside
 cbnz w0,1f
 ldp x0,x1,[sp,#16]
 ldp x2,x3,[sp,#32]
 ldp d0,d1,[sp,#48]
 ldp x29,x30,[sp],#64
 // Displaced instruction from the original pointInside method.
 stp d9,d8,[sp,#-0x30]!
 b _inside_body
1:
 ldp x29,x30,[sp],#64
 mov w0,#1
 ret

// Fix the self-profile's first icon lookup, before its texture is displayed.
// This exact caller is UserCell::update -> CharacterDef::icon; x21 holds its
// profile. Friend/remote profiles and every other icon caller are untouched.
.p2align 2
.globl _stable_self_icon
_stable_self_icon:
 adr x9,plugin_data_address
 ldr x10,[x9,#0x278]
 mov w11,#0x3140
 movk w11,#2,lsl #16
 add x10,x10,x11
 cmp x30,x10
 b.ne 1f
 cbz x21,1f
 ldrb w10,[x21,#0x109]
 tbz w10,#0,1f
 add x10,x9,#0x3c
 ldar w10,[x10]
 cmp w10,#0x80
 b.hi 1f
 ldr x10,[x9,#0x808]
 cbz x10,1f
 ldr w11,[x10,#0xc]
 str w11,[x21,#0x40]
 ldrb w11,[x10,#0xc9]
 ldrb w12,[x10,#0xca]
 strb w11,[x21,#0xb8]
 strb w12,[x21,#0xb9]
 cmp w12,#0
 cset w12,eq
 and w2,w11,w12
 mov x0,x10
1:
 stp x28,x27,[sp,#-0x40]!
 b _icon_body

.p2align 2
.globl _metadata_name
_metadata_name:
 adr x9,metadata_names
 mov x10,x0
1:
 ldrb w11,[x9]
 cbz w11,4f
 mov x12,x9
 mov x13,x10
2:
 ldrb w11,[x12],#1
 ldrb w14,[x13],#1
 cmp w14,#65
 b.lo 5f
 cmp w14,#90
 b.hi 5f
 add w14,w14,#32
5:
 cmp w11,w14
 b.ne 3f
 cbnz w11,2b
 mov w0,#0
 ret
3:
 ldrb w11,[x9],#1
 cbnz w11,3b
 b 1b
4:
 mov w0,#1
 ret
metadata_names: .asciz "song.json"
 .asciz "songlist.json"
 .asciz "songlist"
 .asciz "songlist.txt"
 .asciz "song.txt"
 .byte 0
.p2align 2
// Wrap only this import's NSJSONSerialization call; never other JSON readers.
.globl _metadata_json
_metadata_json:
 stp x29,x30,[sp,#-32]!
 bl _objc_msgSend
 cbz x0,1f
 bl normalize_metadata
 cbz x0,2f
 str x0,[sp,#16]
 adr x0,metadata_normalized
 bl _import_log
 ldr x0,[sp,#16]
 b 3f
1:
 adr x0,metadata_parse_failed
 b 4f
2:
 adr x0,metadata_shape_failed
4:
 bl _import_log
 mov x0,#0
3:
 ldp x29,x30,[sp],#32
 ret
// Helpers take Foundation objects and UTF-8 keys. Returned objects are kept in
// the caller's autorelease pool. The parsed dictionary is mutable (options=1).
dict_get:
 stp x29,x30,[sp,#-32]!
 stp x20,x19,[sp,#16]
 mov x19,x0
 mov x0,x1
 bl nsstring
 mov x20,x0
 adr x0,object_for_key
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 mov x2,x20
 bl _objc_msgSend
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#32
 ret
dict_set:
 stp x29,x30,[sp,#-48]!
 stp x20,x19,[sp,#16]
 str x21,[sp,#32]
 mov x19,x0
 mov x20,x2
 mov x0,x1
 bl nsstring
 mov x21,x0
 adr x0,set_object_key
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 mov x2,x20
 mov x3,x21
 bl _objc_msgSend
 ldr x21,[sp,#32]
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#48
 ret
is_class:
 stp x29,x30,[sp,#-32]!
 stp x20,x19,[sp,#16]
 mov x19,x0
 mov x0,x1
 bl _objc_getClass
 // x2 is caller-saved: sel_registerName may overwrite it. Keep the class
 // in x20 until the final objc_msgSend argument registers are assembled.
 mov x20,x0
 adr x0,is_kind
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 mov x2,x20
 bl _objc_msgSend
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#32
 ret
normalize_metadata:
 stp x29,x30,[sp,#-64]!
 stp x20,x19,[sp,#16]
 stp x22,x21,[sp,#32]
 stp x24,x23,[sp,#48]
 mov x19,x0
 cbz x19,9f
 adr x1,array_class
 bl is_class
 cbnz w0,2f
 mov x0,x19
 adr x1,dictionary_class
 bl is_class
 cbz w0,8f
 mov x0,x19
 adr x1,songs_key
 bl dict_get
 cbz x0,3f
 mov x19,x0
 adr x1,array_class
 bl is_class
 cbz w0,8f
2:
 adr x0,count_selector
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 bl _objc_msgSend
 cmp x0,#1
 b.ne 8f
 adr x0,object_at_index
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 mov x2,#0
 bl _objc_msgSend
 mov x19,x0
3:
 mov x0,x19
 adr x1,dictionary_class
 bl is_class
 cbz w0,8f
 mov x0,x19
 adr x1,difficulties_key
 bl dict_get
 mov x20,x0
 adr x1,array_class
 bl is_class
 cbz w0,7f
 adr x0,mutable_array_class
 bl _objc_getClass
 mov x21,x0
 adr x0,array_selector
 bl _sel_registerName
 mov x1,x0
 mov x0,x21
 bl _objc_msgSend
 mov x21,x0
 adr x0,count_selector
 bl _sel_registerName
 mov x1,x0
 mov x0,x20
 bl _objc_msgSend
 mov x22,x0
 mov x23,#0
4:
 cmp x23,x22
 b.hs 6f
 adr x0,object_at_index
 bl _sel_registerName
 mov x1,x0
 mov x0,x20
 mov x2,x23
 bl _objc_msgSend
 mov x24,x0
 adr x1,rating_key
 mov x2,#0
 bl _metadata_integer
 tbnz x0,#63,5f
 adr x0,add_object_selector
 bl _sel_registerName
 mov x1,x0
 mov x0,x21
 mov x2,x24
 bl _objc_msgSend
5:
 add x23,x23,#1
 b 4b
6:
 mov x0,x19
 adr x1,difficulties_key
 mov x2,x21
 bl dict_set
7:
 mov x0,x19
 b 9f
8:
 mov x0,#0
9:
 ldp x24,x23,[sp,#48]
 ldp x22,x21,[sp,#32]
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#64
 ret
// _jacket is honored if present on disk. Otherwise choose a conventional name
// from the metadata directory; subsequent existing image/path checks still run.
.globl _jacket_lookup
_jacket_lookup:
 stp x29,x30,[sp,#-64]!
 stp x20,x19,[sp,#16]
 stp x22,x21,[sp,#32]
 str x23,[sp,#48]
 ldr x21,[sp,#0x110] // original frame sp+0xd0
 bl _metadata_string
 mov x19,x0
 bl jacket_exists
 cbnz w0,4f
 adr x20,jacket_names
1:
 ldrb w8,[x20]
 cbz w8,4f
 mov x0,x20
 bl nsstring
 mov x22,x0
 bl jacket_exists
 cbnz w0,3f
2:
 ldrb w8,[x20],#1
 cbnz w8,2b
 b 1b
3:
 mov x19,x22
4:
 mov x0,x19
 ldr x23,[sp,#48]
 ldp x22,x21,[sp,#32]
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#64
 ret
jacket_exists:
 stp x29,x30,[sp,#-32]!
 stp x23,x19,[sp,#16]
 mov x19,x0
 adr x0,append_component
 bl _sel_registerName
 mov x1,x0
 mov x0,x21
 mov x2,x19
 bl _objc_msgSend
 mov x19,x0
 adr x0,file_manager
 bl _objc_getClass
 mov x23,x0
 adr x0,default_manager
 bl _sel_registerName
 mov x1,x0
 mov x0,x23
 bl _objc_msgSend
 mov x23,x0
 adr x0,file_exists_selector
 bl _sel_registerName
 mov x1,x0
 mov x0,x23
 mov x2,x19
 bl _objc_msgSend
 ldp x23,x19,[sp,#16]
 ldp x29,x30,[sp],#32
 ret
array_class: .asciz "NSArray"
dictionary_class: .asciz "NSDictionary"
mutable_array_class: .asciz "NSMutableArray"
is_kind: .asciz "isKindOfClass:"
set_object_key: .asciz "setObject:forKey:"
count_selector: .asciz "count"
array_selector: .asciz "array"
add_object_selector: .asciz "addObject:"
songs_key: .asciz "songs"
difficulties_key: .asciz "difficulties"
rating_key: .asciz "rating"
file_exists_selector: .asciz "fileExistsAtPath:"
jacket_names: .asciz "1080_base.jpg"
 .asciz "base.jpg"
 .asciz "1080_base.png"
 .asciz "base.png"
 .asciz "jacket.jpg"
 .asciz "cover.jpg"
 .asciz "jacket.png"
 .asciz "cover.png"
 .byte 0

.p2align 2
.globl _import_entry
_import_entry:
 stp x29,x30,[sp,#-48]!
 stp x0,x1,[sp,#16]
 str x2,[sp,#32]
 adr x0,import_revision
 bl _import_log
 ldp x0,x1,[sp,#16]
 ldr x2,[sp,#32]
 ldp x29,x30,[sp],#48
 stp d9,d8,[sp,#-0x70]!
 b _import_entry_body
import_revision: .asciz "windowfix-r22: 开始检查导入包（类型检查寄存器修复）"
metadata_normalized: .asciz "windowfix-r22: JSON 单曲信息和难度筛选通过"
metadata_parse_failed: .asciz "windowfix-r22: JSON 解析失败，请检查信息文件的编码和语法"
metadata_shape_failed: .asciz "windowfix-r22: 信息结构无效，需要单曲对象或只有一首歌的 songs 数组"

// Cover copying is separate from the song transaction: verify the parent,
// distinguish a missing bundled source, and encode the validated song jacket
// as real PNG if no default cover can be read. All calls run on import worker.
.p2align 2
.globl _write_pack_cover
_write_pack_cover:
 stp x29,x30,[sp,#-96]!
 stp x20,x19,[sp,#16]
 stp x22,x21,[sp,#32]
 stp x24,x23,[sp,#48]
 stp x26,x25,[sp,#64]
 mov x19,x0 // bundled cover NSData, possibly nil
 mov x20,x2 // final destination NSString
 ldr x21,[sp,#0x100] // original sp+0xa0, validated song jacket NSData
 str xzr,[sp,#80] // NSError slot
 adr x0,delete_last_component
 bl _sel_registerName
 mov x1,x0
 mov x0,x20
 bl _objc_msgSend
 mov x22,x0
 cbz x22,7f
 adr x0,file_manager
 bl _objc_getClass
 mov x23,x0
 adr x0,default_manager
 bl _sel_registerName
 mov x1,x0
 mov x0,x23
 bl _objc_msgSend
 mov x23,x0
 adr x0,create_directory_selector
 bl _sel_registerName
 mov x1,x0
 mov x0,x23
 mov x2,x22
 mov w3,#1
 mov x4,#0
 add x5,sp,#80
 bl _objc_msgSend
 cbz w0,7f
 cbz x19,2f
 adr x0,length_selector
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 bl _objc_msgSend
 cbnz x0,3f
2:
 adr x0,cover_fallback_message
 bl _import_log
 adr x0,image_class
 bl _objc_getClass
 mov x24,x0
 adr x0,image_with_data
 bl _sel_registerName
 mov x1,x0
 mov x0,x24
 mov x2,x21
 bl _objc_msgSend
 cbz x0,6f
 bl _UIImagePNGRepresentation
 mov x19,x0
 cbz x19,6f
3:
 adr x0,write_data_options_error
 bl _sel_registerName
 mov x25,x0
 mov x1,x25
 mov x0,x19
 mov x2,x20
 mov w3,#1 // NSDataWritingAtomic
 add x4,sp,#80
 bl _objc_msgSend
 cbnz w0,5f
 adr x0,cover_atomic_retry_message
 bl _import_log
 // Some file providers/protection states reject the atomic rename. Try a
 // normal write; failure remains fatal and no new active catalog is committed.
 str xzr,[sp,#80]
 mov x1,x25
 mov x0,x19
 mov x2,x20
 mov w3,#0
 add x4,sp,#80
 bl _objc_msgSend
 cbz w0,8f
5:
 adr x0,cover_written_message
 bl _import_log
 mov w0,#1
 b 9f
6:
 adr x0,cover_decode_failed_message
 b 4f
7:
 adr x0,cover_directory_failed_message
 b 4f
8:
 adr x0,cover_write_failed_message
4:
 bl _import_log
 // Add NSError's numeric code when Foundation supplied one. No path or
 // localized description is exported, avoiding personal sandbox identifiers.
 ldr x0,[sp,#80]
 cbz x0,1f
 bl log_cover_error_code
1:
 mov w0,#0
9:
 ldp x26,x25,[sp,#64]
 ldp x24,x23,[sp,#48]
 ldp x22,x21,[sp,#32]
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#96
 ret
log_cover_error_code:
 sub sp,sp,#320
 stp x29,x30,[sp,#40]
 str x19,[sp,#16]
 mov x19,x0
 adr x0,error_code_selector
 bl _sel_registerName
 mov x1,x0
 mov x0,x19
 bl _objc_msgSend
 str x0,[sp,#32] // temporarily keep code
 add x0,sp,#64
 mov w1,#240
 adr x2,cover_error_format
 ldr x8,[sp,#32]
 str x8,[sp] // Darwin ARM64 variadic integer argument lives on the stack
 bl _snprintf
 add x0,sp,#64
 bl _import_log
 ldr x19,[sp,#16]
 ldp x29,x30,[sp,#40]
 add sp,sp,#320
 ret

length_selector: .asciz "length"
delete_last_component: .asciz "stringByDeletingLastPathComponent"
create_directory_selector: .asciz "createDirectoryAtPath:withIntermediateDirectories:attributes:error:"
image_class: .asciz "UIImage"
image_with_data: .asciz "imageWithData:"
write_data_options_error: .asciz "writeToFile:options:error:"
error_code_selector: .asciz "code"
cover_error_format: .asciz "windowfix-r22: 曲包封面 Foundation 错误码 %lld"
cover_fallback_message: .asciz "windowfix-r22: 内置曲包封面未读到，使用已验证的歌曲曲绘生成 PNG"
cover_atomic_retry_message: .asciz "windowfix-r22: 封面原子写入失败，尝试普通写入"
cover_written_message: .asciz "windowfix-r22: 曲包封面写入成功"
cover_decode_failed_message: .asciz "windowfix-r22: 曲包封面来源不可用，曲绘 PNG 编码失败"
cover_directory_failed_message: .asciz "windowfix-r22: 无法创建曲包封面目标目录"
cover_write_failed_message: .asciz "windowfix-r22: 曲包封面两次写入均失败"

// Reloading StartScene alone retains the existing SongManager catalog.
// Follow the game's own reload order: packs, songs, unlock definitions, then
// enter StartScene. Called exclusively from import nativeFrame on engine thread.
.p2align 2
.globl _reload_catalogs
_reload_catalogs:
 stp x29,x30,[sp,#-48]!
 stp x20,x19,[sp,#16]
 str x21,[sp,#32]
 mov x29,sp
 adr x8,_plugin_data_address
 ldr x19,[x8,#0x278]
 cbz x19,9f
 movz x8,#0x81d8
 movk x8,#0x167,lsl #16
 ldr x20,[x19,x8]
 cbz x20,8f
 ldr x21,[x20,#0x20]
 cbz x21,8f
 // Packs and songs share the same native owner. Both loaders clear/rebuild
 // their own containers, matching native reload (main + 0x13ccdc..0x13cd0c).
 mov x0,x21
 movz x8,#0xde88
 movk x8,#0xc7,lsl #16
 add x8,x19,x8
 blr x8
 mov x0,x21
 movz x8,#0xf140
 movk x8,#0xc7,lsl #16
 add x8,x19,x8
 blr x8
 ldr x0,[x20,#0x38]
 cbz x0,7f
 movz x8,#0x6b54
 movk x8,#0xbe,lsl #16
 add x8,x19,x8
 blr x8
7:
 adr x0,catalog_reloaded_message
 bl _import_log
8:
 movz x8,#0x5604
 movk x8,#4,lsl #16
 add x8,x19,x8
 blr x8
9:
 ldr x21,[sp,#32]
 ldp x20,x19,[sp,#16]
 ldp x29,x30,[sp],#48
 ret
catalog_reloaded_message: .asciz "windowfix-r22: 原生曲包、歌曲及解锁列表已重新读取"

.p2align 2
.globl _library_open_bridge
_library_open_bridge:
 adr x16,_state_address
 ldr x16,[x16,#80]
 cbz x16,1f
 br x16
1: ret
_library_poll:
 stp x29,x30,[sp,#-16]!
 adr x16,_state_address
 ldr x16,[x16,#88]
 cbz x16,1f
 blr x16
 cbz w0,1f
 bl _import_request_reload
1:
 ldp x29,x30,[sp],#16
 ret

// The existing fullPath resolver checks traversal and existence after this gate.
// Recover the validated C filename from x22 std::string; x25 now holds prefix NSString.
.globl _background_path_gate
_background_path_gate:
 cbnz w0,Lasset_allowed
 mov x9,x22
 ldrsb w8,[x22,#0x17]
 tbz w8,#31,Lasset_string_ready
 ldr x9,[x22]
Lasset_string_ready:
 ldrb w8,[x9]
 cmp w8,#105
 b.ne Lasset_denied
 ldrb w8,[x9,#1]
 cmp w8,#109
 b.ne Lasset_denied
 ldrb w8,[x9,#2]
 cmp w8,#103
 b.ne Lasset_denied
 ldrb w8,[x9,#3]
 cmp w8,#47
 b.ne Lasset_denied
 ldrb w8,[x9,#4]
 cmp w8,#98
 b.ne Lasset_denied
 ldrb w8,[x9,#5]
 cmp w8,#103
 b.ne Lasset_denied
 ldrb w8,[x9,#6]
 cmp w8,#47
 b.ne Lasset_denied
Lasset_allowed:
 b _asset_path_continue
Lasset_denied:
 b _asset_path_fallback
