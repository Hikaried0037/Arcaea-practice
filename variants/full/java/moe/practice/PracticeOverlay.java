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
    static native void catalogChanged();
    private static native void initAssets(String path);
    private static native String chartAsset();
    private static native void pitchMode(boolean changesPitch);
    private static native void flowMode(boolean fixed);
    private static native void previewMode(boolean on,int target);
    private static native void simulatorMode(boolean on);
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
    private Switch pitchSwitch;
    private PracticeTimeline timeline;
    private FrameLayout simulator;
    private LinearLayout simulatorControls;
    private TextView scrubText,transportState;
    private int previewTime;
    private boolean simulatorOpened,simulatorPlaying;
    private Button tab,importTab;
    private int current=-1;
    private boolean opened=false;
    private final int purple=0xff6f568d,ink=0xff30283e;
    public static void attach(Activity a){
        try {prepare(a);int state=boot();if(state!=1){Toast.makeText(a,"练习插件未加载："+state,Toast.LENGTH_LONG).show();return;}new PracticeOverlay(a);}
        catch(Throwable e){android.util.Log.e("ArcPractice","overlay initialization failed",e);}
    }
    public static void prepare(Activity a){try{ChartLibrary.prepare(a);initAssets(ChartLibrary.root(a).getAbsolutePath());}catch(Exception e){throw new IllegalStateException("无法初始化谱面资源",e);}}
    private int dp(float n){return (int)(activity.getResources().getDisplayMetrics().density*n+.5f);}
    private GradientDrawable background(int color,int border){GradientDrawable g=new GradientDrawable();g.setColor(color);g.setCornerRadius(dp(3));g.setStroke(dp(1),border);return g;}
    private TextView text(String s,int size){TextView t=new TextView(activity);t.setIncludeFontPadding(false);t.setText(s);t.setTextSize(size);t.setTextColor(ink);if(font!=null)t.setTypeface(font);return t;}
    private Button button(String s,Runnable action){Button t=new Button(activity);t.setText(s);t.setTextSize(12);t.setTextColor(purple);t.setAllCaps(false);t.setGravity(Gravity.CENTER);t.setMaxLines(1);t.setIncludeFontPadding(true);if(android.os.Build.VERSION.SDK_INT>=26)t.setAutoSizeTextTypeUniformWithConfiguration(6,12,1,android.util.TypedValue.COMPLEX_UNIT_SP);else t.setTextSize(android.util.TypedValue.COMPLEX_UNIT_PX,Math.min(12*activity.getResources().getDisplayMetrics().scaledDensity,dp(18)));if(font!=null)t.setTypeface(font);t.setBackground(background(0xfff6f1fb,0xffcbbddd));t.setMinHeight(0);t.setMinimumHeight(0);t.setPadding(dp(8),dp(2),dp(8),dp(2));t.setOnClickListener(v->action.run());return t;}
    private LinearLayout row(){LinearLayout r=new LinearLayout(activity);r.setGravity(Gravity.CENTER_VERTICAL);r.setPadding(0,dp(3),0,dp(3));panel.addView(r,new LinearLayout.LayoutParams(-1,-2));return r;}
    private void addButton(LinearLayout r,String s,Runnable action){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(36),1);p.setMargins(dp(2),0,dp(2),0);r.addView(button(s,action),p);}
    private EditText timeInput(String value){EditText e=new EditText(activity);e.setSingleLine(true);e.setTextColor(ink);e.setTextSize(15);e.setInputType(8194);e.setImeOptions(EditorInfo.IME_FLAG_NO_EXTRACT_UI|EditorInfo.IME_ACTION_DONE);e.setOnEditorActionListener((v,action,event)->{hideKeyboard();return true;});e.setText(value);e.setSelectAllOnFocus(true);e.setPadding(dp(8),0,dp(8),0);e.setBackground(background(0xfffaf8fd,0xffcbbddd));return e;}
    private Switch toggle(String label){Switch s=new Switch(activity);s.setText(label);s.setTextColor(ink);s.setTextSize(13);panel.addView(s,new LinearLayout.LayoutParams(-1,dp(37)));s.setOnCheckedChangeListener((v,on)->apply(false));return s;}
    private PracticeOverlay(Activity a){
        activity=a;
        try {font=Typeface.createFromAsset(a.getAssets(),"Fonts/NotoSansCJKsc-Regular.otf");}catch(Throwable ignored){try{font=Typeface.createFromAsset(a.getAssets(),"Fonts/Exo-Regular.ttf");}catch(Throwable unused){}}
        root=new FrameLayout(a);
        a.addContentView(root,new android.view.ViewGroup.LayoutParams(-1,-1));
        panel=new LinearLayout(a);panel.setOrientation(LinearLayout.VERTICAL);panel.setPadding(dp(16),dp(12),dp(16),dp(12));panel.setBackground(background(0xffeee9f5,0xffc0afd6));panel.setElevation(dp(12));
        FrameLayout.LayoutParams pp=new FrameLayout.LayoutParams(dp(310),-2,Gravity.TOP|Gravity.RIGHT);pp.setMargins(0,dp(48),dp(12),dp(8));
        ScrollView scroll=new ScrollView(a);scroll.setFillViewport(false);scroll.addView(panel);root.addView(scroll,pp);scroll.setVisibility(View.GONE);
        tab=button("◇ PRACTICE",()->{opened=!opened;scroll.setVisibility(opened?View.VISIBLE:View.GONE);});
        FrameLayout.LayoutParams tp=new FrameLayout.LayoutParams(dp(125),dp(35),Gravity.TOP|Gravity.RIGHT);tp.setMargins(0,dp(8),dp(142),0);root.addView(tab,tp);
        ChartLibrary library=ChartLibrary.attach(a);
        importTab=button("＋ 导入谱面",library::show);FrameLayout.LayoutParams ip=new FrameLayout.LayoutParams(dp(125),dp(35),Gravity.TOP|Gravity.RIGHT);ip.setMargins(0,dp(8),dp(12),0);root.addView(importTab,ip);
        LinearLayout title=row();TextView heading=text("FRAGMENT PRACTICE",18);heading.setTextColor(purple);title.addView(heading,new LinearLayout.LayoutParams(0,-2,1));title.addView(button("×",()->{opened=false;scroll.setVisibility(View.GONE);hideKeyboard();}),new LinearLayout.LayoutParams(dp(32),dp(30)));
        timer=text("进入曲目后可标记片段",13);panel.addView(timer);
        TextView hint=text("时间以秒为单位 · 起点前预备实际 3 秒",11);hint.setPadding(0,dp(4),0,dp(3));panel.addView(hint);
        LinearLayout times=row();times.addView(text("A  ",15));start=timeInput("0.000");times.addView(start,new LinearLayout.LayoutParams(0,dp(35),1));times.addView(text("  B  ",15));end=timeInput("30.000");times.addView(end,new LinearLayout.LayoutParams(0,dp(35),1));
        LinearLayout markers=row();addButton(markers,"标记 A",()->mark(start));addButton(markers,"标记 B",()->mark(end));addButton(markers,"应用时间",()->apply(true));
        LinearLayout selection=row();addButton(selection,"进入全屏选段",()->{if(current<0){toast("请先进入曲目");return;}hideKeyboard();opened=false;scroll.setVisibility(View.GONE);openSimulator();});
        enabled=toggle("练习模式");auto=toggle("自动播放");loop=toggle("A → B 循环");
        pitchSwitch=toggle("倍速同时改变音高");pitchSwitch.setOnCheckedChangeListener((v,on)->{pitchMode(on);a.getSharedPreferences("practice",0).edit().putBoolean("pitch",on).apply();});pitchSwitch.setChecked(a.getSharedPreferences("practice",0).getBoolean("pitch",true));pitchMode(pitchSwitch.isChecked());
        Switch flow=toggle("流速不随倍速变化");flow.setOnCheckedChangeListener((v,on)->{flowMode(on);a.getSharedPreferences("practice",0).edit().putBoolean("fixedFlow",on).apply();if(current>=0)toast("流速变化将自动重播；选段位置保留");});flow.setChecked(a.getSharedPreferences("practice",0).getBoolean("fixedFlow",false));flowMode(flow.isChecked());
        LinearLayout speeds=row();speedText=text("速度 1.00×",14);speeds.addView(speedText,new LinearLayout.LayoutParams(0,-2,1));
        final int minRate=25,maxRate=200;
        SeekBar bar=new SeekBar(a);bar.setMax(maxRate-minRate);bar.setProgress(100-minRate);panel.addView(bar,new LinearLayout.LayoutParams(-1,dp(32)));bar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){apply(false);}public void onProgressChanged(SeekBar s,int p,boolean user){speed=(p+minRate)/100f;speedText.setText(String.format(Locale.US,"速度 %.2f×",speed));if(!user)apply(false);}});
        speeds.addView(button("−",()->bar.setProgress(Math.max(0,bar.getProgress()-1))),new LinearLayout.LayoutParams(dp(38),dp(28)));
        speeds.addView(button("＋",()->bar.setProgress(Math.min(bar.getMax(),bar.getProgress()+1))),new LinearLayout.LayoutParams(dp(38),dp(28)));
        LinearLayout presets=row();for(int rate:new int[]{50,80,100,120,150})addButton(presets,String.format(Locale.US,"%.2f×",rate/100f),()->bar.setProgress(rate-minRate));
        TextView opacityText=text("面板透明度",12);panel.addView(opacityText);SeekBar opacity=new SeekBar(a);opacity.setMax(70);panel.addView(opacity,new LinearLayout.LayoutParams(-1,dp(28)));opacity.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}public void onProgressChanged(SeekBar s,int p,boolean user){panel.setAlpha(1-p/100f);tab.setAlpha(1-p/100f);importTab.setAlpha(1-p/100f);if(simulatorControls!=null)simulatorControls.setAlpha(1-p/100f);opacityText.setText("面板透明度 "+p+"%（0% 不透明 / 70% 几乎透明）");a.getSharedPreferences("practice",0).edit().putInt("opacity",p).apply();}});opacity.setProgress(a.getSharedPreferences("practice",0).getInt("opacity",0));
        LinearLayout replayRow=row();addButton(replayRow,"↶ 重播片段",()->{if(current<0){toast("请先进入曲目");return;}enabled.setChecked(true);if(apply(true)){replay();opened=false;scroll.setVisibility(View.GONE);}});
        TextView foot=text("关闭音高开关以保持原调（极慢速可能有音色变化）。\n全屏选段使用游戏本身的谱面与场景效果。",10);foot.setPadding(0,dp(5),0,0);panel.addView(foot);
        simulator=new FrameLayout(a);simulator.setClickable(true);simulator.setVisibility(View.GONE);root.addView(simulator,new FrameLayout.LayoutParams(-1,-1));
        timeline=new PracticeTimeline(a,new PracticeTimeline.Listener(){public void seek(int time){previewTime=time;simulatorPlaying=false;previewMode(true,time);}public void marker(boolean isStart,int time){(isStart?start:end).setText(String.format(Locale.US,"%.3f",time/1000.0));apply(false);}});
        FrameLayout.LayoutParams timelineParams=new FrameLayout.LayoutParams(-1,dp(78),Gravity.TOP);timelineParams.setMargins(dp(12),dp(8),dp(12),0);simulator.addView(timeline,timelineParams);
        simulatorControls=new LinearLayout(a);simulatorControls.setOrientation(LinearLayout.VERTICAL);simulatorControls.setPadding(dp(10),dp(8),dp(10),dp(8));simulatorControls.setBackground(background(0x85352d42,0x99ffffff));simulatorControls.setAlpha(1-a.getSharedPreferences("practice",0).getInt("opacity",0)/100f);
        FrameLayout.LayoutParams controlsParams=new FrameLayout.LayoutParams(dp(235),-2,Gravity.TOP|Gravity.LEFT);controlsParams.setMargins(dp(12),dp(94),0,0);simulator.addView(simulatorControls,controlsParams);
        scrubText=text("全屏谱面选段",13);scrubText.setTextColor(Color.WHITE);simulatorControls.addView(scrubText);
        LinearLayout simSpeed=new LinearLayout(a);simulatorControls.addView(simSpeed);Button less=simButton("−",()->bar.setProgress(Math.max(0,bar.getProgress()-1)));Button more=simButton("＋",()->bar.setProgress(Math.min(bar.getMax(),bar.getProgress()+1)));simSpeed.addView(less,new LinearLayout.LayoutParams(0,dp(36),1));simSpeed.addView(more,new LinearLayout.LayoutParams(0,dp(36),1));
        simulatorControls.addView(simButton("循环练习 · 开 / 关",()->loop.setChecked(!loop.isChecked())),new LinearLayout.LayoutParams(-1,dp(36)));
        simulatorControls.addView(simButton("播放 / 暂停",()->{simulatorPlaying=!simulatorPlaying;previewMode(!simulatorPlaying,Math.max(0,current));}),new LinearLayout.LayoutParams(-1,dp(36)));
        LinearLayout simMarkers=new LinearLayout(a);simulatorControls.addView(simMarkers);simMarkers.addView(simButton("设为 A",()->simMark(start)),new LinearLayout.LayoutParams(0,dp(36),1));simMarkers.addView(simButton("设为 B",()->simMark(end)),new LinearLayout.LayoutParams(0,dp(36),1));
        simulatorControls.addView(simButton("应用 A → B 并重播",()->{if(apply(true)){closeSimulator();replay();}}),new LinearLayout.LayoutParams(-1,dp(36)));
        Button exit=simButton("退出选段  ←",this::closeSimulator);FrameLayout.LayoutParams exitParams=new FrameLayout.LayoutParams(dp(150),dp(42),Gravity.BOTTOM|Gravity.RIGHT);exitParams.setMargins(0,0,dp(18),dp(16));simulator.addView(exit,exitParams);
        transportState=text("准备片段…",20);transportState.setTextColor(Color.WHITE);transportState.setGravity(Gravity.CENTER);transportState.setPadding(dp(16),dp(10),dp(16),dp(10));transportState.setBackground(background(0xdd30283e,0xffb6a1cf));transportState.setVisibility(View.GONE);FrameLayout.LayoutParams stateParams=new FrameLayout.LayoutParams(-2,-2,Gravity.CENTER);root.addView(transportState,stateParams);
        handler.post(new Runnable(){public void run(){if(a.isFinishing()||a.isDestroyed()){previewMode(false,0);return;}int[] s=status();current=s[1];transportState.setVisibility(s[6]!=0||s[7]>0?View.VISIBLE:View.GONE);transportState.setText(s[6]!=0?"准备谱面与音频…":String.format(Locale.US,"预备 %.1f 秒",s[7]/1000f));timer.setText(current<0&&s[7]==0?"等待曲目 · 练习参数将在曲目中生效":String.format(Locale.US,"%s  ·  循环 %d%s",format(current),s[3],s[4]==0?"":" · 音高处理失败 "+s[4]));if(simulatorOpened){if(current<0&&s[6]==0){closeSimulator();}else{timeline.load(chartAsset());int x=parsedTime(start),y=parsedTime(end);timeline.state(s[2],simulatorPlaying?Math.max(0,current):previewTime,x,y);scrubText.setText(String.format(Locale.US,"%.2f× · 循环%s\n%s%s",speed,loop.isChecked()?"开":"关",format(Math.max(0,current)),s[6]!=0?" · 准备中":s[7]>0?String.format(Locale.US," · 预备 %.1fs",s[7]/1000f):""));}}handler.postDelayed(this,100);}});
    }
    private Button simButton(String label,Runnable action){Button b=button(label,action);b.setTextColor(Color.WHITE);b.setBackground(background(0x454d425d,0x88ffffff));return b;}
    private int parsedTime(EditText input){try{return (int)Math.round(Double.parseDouble(input.getText().toString())*1000);}catch(Exception e){return 0;}}
    private void simMark(EditText input){input.setText(String.format(Locale.US,"%.3f",(simulatorPlaying?Math.max(0,current):previewTime)/1000.0));apply(false);}
    private void openSimulator(){enabled.setChecked(true);apply(false);simulatorMode(true);simulatorOpened=true;simulatorPlaying=false;previewTime=Math.max(0,current);timeline.state(status()[2],previewTime,parsedTime(start),parsedTime(end));simulator.setVisibility(View.VISIBLE);tab.setVisibility(View.GONE);importTab.setVisibility(View.GONE);previewMode(true,previewTime);}
    private void closeSimulator(){simulatorOpened=false;previewMode(false,0);simulatorMode(false);simulator.setVisibility(View.GONE);tab.setVisibility(View.VISIBLE);importTab.setVisibility(View.VISIBLE);}
    private String format(int ms){return String.format(Locale.US,"%02d:%06.3f",Math.max(ms,0)/60000,Math.max(ms,0)%60000/1000.0);}
    private void mark(EditText target){if(current<0){toast("请先进入曲目");return;}target.setText(String.format(Locale.US,"%.3f",current/1000.0));}
    private void toast(String s){Toast.makeText(activity,s,Toast.LENGTH_SHORT).show();}
    private void hideKeyboard(){((InputMethodManager)activity.getSystemService(Context.INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(start.getWindowToken(),0);start.clearFocus();end.clearFocus();}
    private boolean apply(boolean notify){
        if(enabled==null||auto==null||loop==null)return false;
        try{double x=Double.parseDouble(start.getText().toString()),y=Double.parseDouble(end.getText().toString());if(!Double.isFinite(x)||!Double.isFinite(y)||x<0||y-x<1||y>3600)throw new IllegalArgumentException();config(enabled.isChecked(),auto.isChecked(),loop.isChecked(),(int)Math.round(x*1000),(int)Math.round(y*1000),speed);if(notify){hideKeyboard();toast("练习参数已应用");}return true;}catch(Throwable e){if(notify)toast("请输入有效时间：B 至少比 A 晚 1 秒");return false;}
    }
}
