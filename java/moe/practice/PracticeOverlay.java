package moe.practice;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Handler;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.view.inputmethod.EditorInfo;
import android.content.Context;
import android.widget.*;
import java.util.Locale;

public final class PracticeOverlay {
    private static native int boot();
    public static native void frame();
    private static native void config(boolean enabled,boolean autoplay,boolean loop,int a,int b,float speed);
    private static native void replay();
    private static native int[] status();
    static {System.loadLibrary("arcpractice");}
    private final Activity activity;
    private final Handler handler=new Handler();
    private final FrameLayout root;
    private final LinearLayout panel;
    private final TextView timer;
    private final EditText start,end;
    private final Switch enabled,auto,loop;
    private final TextView speedText;
    private Typeface font;
    private float speed=1;
    private int current=-1;
    private boolean opened=false;
    private final int purple=0xff6f568d,ink=0xff30283e;
    public static void attach(Activity a){
        try {int state=boot();if(state!=1){Toast.makeText(a,"练习插件未加载："+state,Toast.LENGTH_LONG).show();return;}new PracticeOverlay(a);}
        catch(Throwable e){android.util.Log.e("ArcPractice","overlay initialization failed",e);}
    }
    private int dp(float n){return (int)(activity.getResources().getDisplayMetrics().density*n+.5f);}
    private GradientDrawable background(int color,int border){GradientDrawable g=new GradientDrawable();g.setColor(color);g.setCornerRadius(dp(3));g.setStroke(dp(1),border);return g;}
    private TextView text(String s,int size){TextView t=new TextView(activity);t.setIncludeFontPadding(false);t.setText(s);t.setTextSize(size);t.setTextColor(ink);if(font!=null)t.setTypeface(font);return t;}
    private Button button(String s,Runnable action){Button t=new Button(activity);t.setText(s);t.setTextSize(12);t.setTextColor(purple);t.setAllCaps(false);if(font!=null)t.setTypeface(font);t.setBackground(background(0xfff6f1fb,0xffcbbddd));t.setMinHeight(0);t.setMinimumHeight(0);t.setPadding(dp(8),dp(2),dp(8),dp(2));t.setOnClickListener(v->action.run());return t;}
    private LinearLayout row(){LinearLayout r=new LinearLayout(activity);r.setGravity(Gravity.CENTER_VERTICAL);r.setPadding(0,dp(3),0,dp(3));panel.addView(r,new LinearLayout.LayoutParams(-1,-2));return r;}
    private void addButton(LinearLayout r,String s,Runnable action){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(36),1);p.setMargins(dp(2),0,dp(2),0);r.addView(button(s,action),p);}
    private EditText timeInput(String value){EditText e=new EditText(activity);e.setSingleLine(true);e.setTextColor(ink);e.setTextSize(15);e.setInputType(8194);e.setImeOptions(EditorInfo.IME_FLAG_NO_EXTRACT_UI|EditorInfo.IME_ACTION_DONE);e.setOnEditorActionListener((v,action,event)->{hideKeyboard();return true;});e.setText(value);e.setSelectAllOnFocus(true);e.setPadding(dp(8),0,dp(8),0);e.setBackground(background(0xfffaf8fd,0xffcbbddd));return e;}
    private Switch toggle(String label){Switch s=new Switch(activity);s.setText(label);s.setTextColor(ink);s.setTextSize(13);panel.addView(s,new LinearLayout.LayoutParams(-1,dp(37)));s.setOnCheckedChangeListener((v,on)->apply(false));return s;}
    private PracticeOverlay(Activity a){
        activity=a;
        try {font=Typeface.createFromAsset(a.getAssets(),"Fonts/NotoSansCJKsc-Regular.otf");}catch(Throwable ignored){try{font=Typeface.createFromAsset(a.getAssets(),"Fonts/Exo-Regular.ttf");}catch(Throwable unused){}}
        root=new FrameLayout(a);
        a.addContentView(root,new android.view.ViewGroup.LayoutParams(-1,-1));
        panel=new LinearLayout(a);panel.setOrientation(LinearLayout.VERTICAL);panel.setPadding(dp(16),dp(12),dp(16),dp(12));panel.setBackground(background(0xf0eee9f5,0xffc0afd6));panel.setElevation(dp(12));
        FrameLayout.LayoutParams pp=new FrameLayout.LayoutParams(dp(310),-2,Gravity.TOP|Gravity.RIGHT);pp.setMargins(0,dp(48),dp(12),dp(8));
        ScrollView scroll=new ScrollView(a);scroll.setFillViewport(false);scroll.addView(panel);root.addView(scroll,pp);scroll.setVisibility(View.GONE);
        Button tab=button("◇ PRACTICE",()->{opened=!opened;scroll.setVisibility(opened?View.VISIBLE:View.GONE);});
        FrameLayout.LayoutParams tp=new FrameLayout.LayoutParams(dp(125),dp(35),Gravity.TOP|Gravity.RIGHT);tp.setMargins(0,dp(8),dp(12),0);root.addView(tab,tp);
        LinearLayout title=row();TextView heading=text("FRAGMENT PRACTICE",18);heading.setTextColor(purple);title.addView(heading,new LinearLayout.LayoutParams(0,-2,1));title.addView(button("×",()->{opened=false;scroll.setVisibility(View.GONE);hideKeyboard();}),new LinearLayout.LayoutParams(dp(32),dp(30)));
        timer=text("进入曲目后可标记片段",13);panel.addView(timer);
        TextView hint=text("时间以秒为单位 · 起点前预备 3 秒",11);hint.setPadding(0,dp(4),0,dp(3));panel.addView(hint);
        LinearLayout times=row();times.addView(text("A  ",15));start=timeInput("0.000");times.addView(start,new LinearLayout.LayoutParams(0,dp(35),1));times.addView(text("  B  ",15));end=timeInput("30.000");times.addView(end,new LinearLayout.LayoutParams(0,dp(35),1));
        LinearLayout markers=row();addButton(markers,"标记 A",()->mark(start));addButton(markers,"标记 B",()->mark(end));addButton(markers,"应用时间",()->apply(true));
        enabled=toggle("练习模式");auto=toggle("自动播放");loop=toggle("A → B 循环");
        LinearLayout speeds=row();speedText=text("速度 1.00×",14);speeds.addView(speedText,new LinearLayout.LayoutParams(0,-2,1));
        SeekBar bar=new SeekBar(a);bar.setMax(35);bar.setProgress(15);panel.addView(bar,new LinearLayout.LayoutParams(-1,dp(32)));bar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){apply(false);}public void onProgressChanged(SeekBar s,int p,boolean user){speed=.25f+p*.05f;speedText.setText(String.format(Locale.US,"速度 %.2f×",speed));apply(false);}});
        LinearLayout presets=row();for(float ratio:new float[]{.5f,.75f,1f,1.25f,1.5f})addButton(presets,String.format(Locale.US,"%.2f×",ratio),()->bar.setProgress(Math.round((ratio-.25f)/.05f)));
        LinearLayout replayRow=row();addButton(replayRow,"↶ 重播片段",()->{if(current<0){toast("请先进入曲目");return;}enabled.setChecked(true);if(apply(true)){replay();opened=false;scroll.setVisibility(View.GONE);}});
        TextView foot=text("重播重新加载谱面。变速会改变音高。\n跨起点音符建议留足预备时间。",10);foot.setPadding(0,dp(5),0,0);panel.addView(foot);
        handler.post(new Runnable(){public void run(){if(a.isFinishing()||a.isDestroyed())return;int[] s=status();current=s[1];timer.setText(current<0?"等待曲目 · 练习参数将在曲目中生效":String.format(Locale.US,"%s  ·  循环 %d",format(current),s[3]));handler.postDelayed(this,200);}});
    }
    private String format(int ms){return String.format(Locale.US,"%02d:%06.3f",Math.max(ms,0)/60000,Math.max(ms,0)%60000/1000.0);}
    private void mark(EditText target){if(current<0){toast("请先进入曲目");return;}target.setText(String.format(Locale.US,"%.3f",current/1000.0));}
    private void toast(String s){Toast.makeText(activity,s,Toast.LENGTH_SHORT).show();}
    private void hideKeyboard(){((InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(start.getWindowToken(),0);start.clearFocus();end.clearFocus();}
    private boolean apply(boolean notify){
        if(enabled==null||auto==null||loop==null)return false;
        try{double x=Double.parseDouble(start.getText().toString()),y=Double.parseDouble(end.getText().toString());if(!Double.isFinite(x)||!Double.isFinite(y)||x<0||y-x<1||y>3600)throw new IllegalArgumentException();config(enabled.isChecked(),auto.isChecked(),loop.isChecked(),(int)Math.round(x*1000),(int)Math.round(y*1000),speed);if(notify){hideKeyboard();toast("练习参数已应用");}return true;}catch(Throwable e){if(notify)toast("请输入有效时间：B 至少比 A 晚 1 秒");return false;}
    }
}
