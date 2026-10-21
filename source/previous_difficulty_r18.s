// UI-thread native difficulty tab routing. Only the verified fix14 game layout.
.text
.p2align 2
.globl _difficulty_tab
_difficulty_tab:
 ldr w1,[x0,#0x10]
 mov x0,x8
 cbz x0,Lreturn
 cmp w1,#4
 b.hi Lreturn
 cmp w1,#3
 b.lo Lapply
 ldr x9,[x0,#0x2f0]
 cbz x9,Lreturn
 ldr x9,[x9]
 cbz x9,Lreturn
 mov x10,x9
 ldr w9,[x10,#0x28]
 cmp w9,w1
 b.eq Ltoggle
 ldr w9,[x10,#0x38]
 cmp w9,w1
 b.ne _difficulty_guard
Ltoggle:
 mov w9,#7
 sub w1,w9,w1
.globl _difficulty_guard
_difficulty_guard:
 cbz x0,Lreturn
 cmp w1,#3
 b.lo Lapply
 cmp w1,#4
 b.hi Lreturn
 // Preserve scene, sender and return address across the availability query.
 stp x0,x2,[sp,#-0x20]!
 stp x29,x30,[sp,#0x10]
 bl _difficulty_has_chart
 mov w8,w0
 ldp x29,x30,[sp,#0x10]
 ldp x0,x2,[sp],#0x20
 cbz w8,Lreturn
 // Rebuild the native filtered list even when the selected row lacks this class.
 // Do not use the row-specific activation path in the original click handler.
 ldr x9,[x0,#0x2f0]
 cbz x9,Lreturn
 ldr x10,[x9]
 cbz x10,Lreturn
 stp x20,x19,[sp,#-0x20]!
 stp x29,x30,[sp,#0x10]
 mov x19,x0
 ldrb w20,[x19,#0x404]
 cmp w1,#4
 cset w8,eq
 strb w8,[x19,#0x404]
 ldr w3,[x10,#0x28]
 mov x0,x9
 mov w2,#1 // force a fresh native filtering pass, not a cached no-op
 bl _difficulty_change
 cbnz w0,Lswitch_success
 strb w20,[x19,#0x404] // failed changes retain the previous preference
 b Lswitch_done
Lswitch_success:
.globl _sound_owner_page
_sound_owner_page:
 .long 0x90000009
 ldr x9,[x9,#0x1d8]
 cbz x9,Lswitch_done
 ldr x0,[x9,#0x10]
 cbz x0,Lswitch_done
 mov w1,#0x10
 mov w2,#1
 mov w3,#0
 mov w4,#0
 bl _difficulty_sound
Lswitch_done:
 ldp x29,x30,[sp,#0x10]
 ldp x20,x19,[sp],#0x20
 ret

// Pure bounded native catalog query. x1 is preserved; x0 returns BOOL.
.globl _difficulty_has_chart
_difficulty_has_chart:
.globl _catalog_owner_page
_catalog_owner_page:
 .long 0x90000009
 ldr x9,[x9,#0x1d8]
 cbz x9,Labsent
 ldr x9,[x9,#0x20]
 cbz x9,Labsent
 add x10,x9,#0x20
 ldr x9,[x9,#0x18]
 add w12,w1,#0x250
 mov w13,#20000
Lnode:
 subs w13,w13,#1
 b.eq Labsent
 cbz x9,Labsent
 cmp x9,x10
 b.eq Labsent
 ldr x11,[x9,#0x38]
 cbz x11,Lnext
 ldrb w11,[x11,x12]
 cbnz w11,Lpresent
Lnext:
 ldr x11,[x9,#8]
 cbz x11,Lup
 mov x9,x11
Lleft:
 subs w13,w13,#1
 b.eq Labsent
 ldr x11,[x9]
 cbz x11,Lnode
 mov x9,x11
 b Lleft
Lup:
 subs w13,w13,#1
 b.eq Labsent
 ldr x11,[x9,#0x10]
 cbz x11,Labsent
 cmp x11,x10
 b.eq Labsent
 ldr x14,[x11]
 cmp x14,x9
 mov x9,x11
 b.eq Lnode
 b Lup
Labsent:
 mov w0,#0
 ret
Lpresent:
 mov w0,#1
 ret
Lreturn:
 ret
Lapply:
 b _difficulty_apply

// Run the game's complete view update first. Repair both alternative tabs after
// every return path, rather than changing two booleans inside that update.
.globl _byd_update
_byd_update:
 cbz x0,Lreturn
 cbz x1,Lreturn
 cbz x2,Lreturn
 ldr x9,[x0,#0x2f0]
 cbz x9,Lreturn
 ldr x9,[x9]
 cbz x9,Lreturn
 stp x22,x21,[sp,#-0x40]!
 stp x20,x19,[sp,#0x10]
 stp x29,x30,[sp,#0x20]
 stp x0,x1,[sp,#0x30]
 bl Loriginal_byd
 ldp x19,x20,[sp,#0x30]
 mov w21,#3
 b Lrepair_button
.globl _etr_update
_etr_update:
 cbz x0,Lreturn
 cbz x1,Lreturn
 cbz x2,Lreturn
 ldr x9,[x0,#0x2f0]
 cbz x9,Lreturn
 ldr x9,[x9]
 cbz x9,Lreturn
 stp x22,x21,[sp,#-0x40]!
 stp x20,x19,[sp,#0x10]
 stp x29,x30,[sp,#0x20]
 stp x0,x1,[sp,#0x30]
 bl Loriginal_etr
 ldp x19,x20,[sp,#0x30]
 mov w21,#4
Lrepair_button:
 mov w22,#0
 cbz x19,Lbutton_state
 cbz x20,Lupdate_done
 ldr x9,[x19,#0x2f0]
 cbz x9,Lbutton_state
 ldr x9,[x9]
 cbz x9,Lbutton_state
 ldr w10,[x9,#0x28]
 cmp w10,#3
 b.eq Lrow_mode
 cmp w10,#4
 b.eq Lrow_mode
 ldr w10,[x9,#0x38]
Lrow_mode:
 mov w9,w10
 cmp w9,#3
 b.eq Lbyd_visible
 cmp w9,#4
 b.eq Letr_visible
 ldrb w9,[x19,#0x404]
 cbz w9,Lbyd_visible
Letr_visible:
 cmp w21,#4
 cset w22,eq
 b Lbutton_state
Lbyd_visible:
 cmp w21,#3
 cset w22,eq
Lbutton_state:
 mov x0,x20
 mov w1,w22
 cbz x0,Lupdate_done
 ldr x8,[x0]
 ldr x8,[x8,#0x150]
 blr x8
 cbz w22,Ltexture_done
 ldr x9,[x19,#0x2f0]
 ldr x9,[x9]
 ldr w9,[x9,#0x28]
 cmp w9,w21
 cset w2,eq
 mov x0,x20
 mov w1,w21
 bl _difficulty_textures
Ltexture_done:
 mov x0,x20
 mov w1,w22
 ldr x8,[x0]
 ldr x8,[x8,#0x558]
 blr x8
Lupdate_done:
 ldp x29,x30,[sp,#0x20]
 ldp x20,x19,[sp,#0x10]
 ldp x22,x21,[sp],#0x40
 ret
Loriginal_byd:
 sub sp,sp,#0x1f0
 b _byd_update_body
Loriginal_etr:
 sub sp,sp,#0x140
 b _etr_update_body

.globl _song_row_nonnull
_song_row_nonnull:
 cbz x8,Lrow_skip
 str x8,[sp,#0x580]
 b _row_continue
Lrow_skip:
 b _row_next
.globl _difficulty_textures
_difficulty_textures:
 stp x20,x19,[sp,#-0x90]!
 stp x22,x21,[sp,#0x10]
 stp x29,x30,[sp,#0x20]
 mov x19,x0
 mov w20,w1
 mov w21,w2
 cmp w20,#3
 b.eq Lpaths_byd
 adr x22,Letr_selected
 adr x1,Letr_normal
 b Lpaths_ready
Lpaths_byd:
 adr x22,Lbyd_selected
 adr x1,Lbyd_normal
Lpaths_ready:
 cmp w21,#0
 csel x1,x22,x1,ne
 add x0,sp,#0x30
 bl _string_construct
 add x0,sp,#0x48
 mov x1,x22
 bl _string_construct
 add x0,sp,#0x60
 mov x1,x22
 bl _string_construct
 mov x0,x19
 add x1,sp,#0x30
 add x2,sp,#0x48
 add x3,sp,#0x60
 mov w4,#0
 bl _button_load_textures
 ldrsb w8,[sp,#0x47]
 tbz w8,#31,Ldelete_second
 ldr x0,[sp,#0x30]
 bl _string_delete
Ldelete_second:
 ldrsb w8,[sp,#0x5f]
 tbz w8,#31,Ldelete_third
 ldr x0,[sp,#0x48]
 bl _string_delete
Ldelete_third:
 ldrsb w8,[sp,#0x77]
 tbz w8,#31,Ltextures_return
 ldr x0,[sp,#0x60]
 bl _string_delete
Ltextures_return:
 ldp x29,x30,[sp,#0x20]
 ldp x22,x21,[sp,#0x10]
 ldp x20,x19,[sp],#0x90
 ret
Lbyd_normal: .asciz "layouts/1080/songselect/difficulty_selector_3.png"
Lbyd_selected: .asciz "layouts/1080/songselect/difficulty_selector_3_selected.png"
Letr_normal: .asciz "layouts/1080/songselect/difficulty_selector_4.png"
Letr_selected: .asciz "layouts/1080/songselect/difficulty_selector_4_selected.png"
.p2align 2
