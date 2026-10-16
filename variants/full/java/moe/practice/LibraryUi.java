package moe.practice;

/** Geometry shared by the runtime layout and viewport regression tests. */
final class LibraryUi {
    static int columns(float widthDp,float fontScale){float buttonWidth=Math.max(112f,52f*Math.max(1f,fontScale)+24f);return widthDp>=buttonWidth*4?4:widthDp>=buttonWidth*2?2:1;}
    static int sidebar(float widthDp,float fontScale){return Math.round(Math.min(widthDp*.36f,Math.max(100,Math.min(200,146*Math.max(1f,fontScale)))));}
    static int headerLimit(int heightPx){return Math.max(1,Math.round(heightPx*.68f));}
    static int buttonHeight(int lineHeight,int padding,int minimum){return Math.max(minimum,lineHeight+padding);}
}
