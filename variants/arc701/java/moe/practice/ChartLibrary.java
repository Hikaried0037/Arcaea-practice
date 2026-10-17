package moe.practice;

import android.app.*;
import android.content.*;
import android.graphics.*;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;

public final class ChartLibrary extends Fragment {
    private File root; private JSONObject songs,packs; private String selectedPack; private Uri pendingZip; private volatile boolean busy;
    private Dialog page; private LinearLayout body; private TextView heading; private String section,openedPack; private Typeface font;
    private final Handler ui=new Handler(Looper.getMainLooper());
    private final ExecutorService pictures=Executors.newFixedThreadPool(2);
    private final android.util.LruCache<String,Bitmap> imageCache=new android.util.LruCache<String,Bitmap>(8*1024*1024){protected int sizeOf(String k,Bitmap b){return b.getByteCount();}};
    private long fingerprint; private int pageGeneration; private ArrayList<FileObserver> observers=new ArrayList<>();
    private final Runnable check=()->refresh(false);
    private int pageWidth,pageHeight;private HeaderScroll pageHeader;
    public static File root(Context c){return new File(android.os.Environment.getExternalStorageDirectory(),"Arc701");}
    public static synchronized void prepare(Context c)throws Exception {
        File r=root(c);if(!new File(r,"songs/songlist").isFile())throw new IOException("Arc701 游戏资源缺失");recover(r);
        for(String n:new String[]{"songlist","packlist"}){
            File original=new File(r,"catalog-"+n+".json"),current=new File(r,"songs/"+n),last=new File(r,".practice-last-"+n);
            byte[] bytes=read(new FileInputStream(current));
            if(!original.exists()||(last.exists()&&!Arrays.equals(bytes,read(new FileInputStream(last))))){
                JSONObject incoming=new JSONObject(new String(bytes,"UTF-8"));
                if(n.equals("packlist")&&original.exists()){
                    JSONObject previous=json(original);JSONArray definitions=previous.optJSONArray("practice_sections");
                    if(definitions!=null)incoming.put("practice_sections",definitions);
                    JSONObject snapshot=last.exists()?json(last):new JSONObject();JSONArray old=snapshot.optJSONArray("packs"), fresh=incoming.optJSONArray("packs");
                    if(old!=null&&fresh!=null){LibraryCatalog model=new LibraryCatalog(new JSONObject().put("songs",new JSONArray()),previous);
                        for(int i=0;i<fresh.length();i++){JSONObject pack=fresh.getJSONObject(i),saved=model.findPack(pack.optString("id"));if(saved==null||!saved.optString("section").startsWith("practice_"))continue;
                            for(int j=0;j<old.length();j++)if(old.getJSONObject(j).optString("id").equals(pack.optString("id"))&&old.getJSONObject(j).optString("section").equals(pack.optString("section")))pack.put("section",saved.getString("section"));
                        }
                    }
                }
                writeJson(original,incoming);
            }
            writeJson(original,json(original));
        }
        regenerate(c);write(new File(r,"theme-mode"),new byte[]{(byte)(c.getSharedPreferences("practice",0).getBoolean("theme",false)?1:0)});
    }
    static byte[] read(InputStream input)throws IOException {try(InputStream in=input;ByteArrayOutputStream out=new ByteArrayOutputStream()){byte[] b=new byte[32768];int n;while((n=in.read(b))!=-1)out.write(b,0,n);return out.toByteArray();}}
    static void write(File f,byte[] bytes)throws IOException {
        if(f.isFile()&&f.length()==bytes.length&&Arrays.equals(bytes,read(new FileInputStream(f))))return;
        f.getParentFile().mkdirs();android.util.AtomicFile a=new android.util.AtomicFile(f);FileOutputStream s=a.startWrite();try{s.write(bytes);a.finishWrite(s);}catch(IOException e){a.failWrite(s);throw e;}
    }
    private static JSONObject json(File f)throws Exception{return new JSONObject(new String(read(new FileInputStream(f)),"UTF-8"));}
    private static void writeJson(File f,JSONObject o)throws Exception{write(f,LibraryCatalog.pretty(o).getBytes("UTF-8"));}
    private static void recover(File r)throws Exception {
        File journal=new File(r,".practice-catalog-transaction.json");if(!journal.exists())return;JSONObject j=json(journal);
        new LibraryCatalog(j.getJSONObject("songs"),j.getJSONObject("packs"));
        writeJson(new File(r,"catalog-songlist.json"),j.getJSONObject("songs"));writeJson(new File(r,"catalog-packlist.json"),j.getJSONObject("packs"));
        if(!journal.delete())throw new IOException("无法完成曲库事务");
    }
    static synchronized void regenerate(Context c)throws Exception {
        File r=root(c);JSONObject s=json(new File(r,"catalog-songlist.json")),p=json(new File(r,"catalog-packlist.json"));
        LibraryCatalog model=new LibraryCatalog(s,p);
        if(PackCovers.ensure(c,r,p))writeJson(new File(r,"catalog-packlist.json"),p);
        if(c.getSharedPreferences("practice",0).getBoolean("theme",false)){JSONArray a=s.getJSONArray("songs");for(int i=0;i<a.length();i++){JSONObject song=a.getJSONObject(i);theme(song);JSONArray d=song.optJSONArray("difficulties");if(d!=null)for(int j=0;j<d.length();j++)theme(d.getJSONObject(j));}}
        writeJson(new File(r,"songs/songlist"),s);writeJson(new File(r,"songs/packlist"),model.runtimePacks());
        for(String n:new String[]{"songlist","packlist"})write(new File(r,".practice-last-"+n),read(new FileInputStream(new File(r,"songs/"+n))));
    }
    private static void theme(JSONObject s)throws Exception{s.put("bg","finale_conflict");s.put("bg_inverse","finale_conflict");s.put("bgOverride","finale_conflict");s.put("track","dark_vs");}
    private interface Change {void run(LibraryCatalog model)throws Exception;}
    private synchronized void mutate(Change change)throws Exception {
        load();JSONObject before=new JSONObject().put("songs",new JSONObject(songs.toString())).put("packs",new JSONObject(packs.toString()));
        LibraryCatalog model=new LibraryCatalog(songs,packs);change.run(model);commit(songs,packs,before);
    }
    private synchronized void commit(JSONObject s,JSONObject p,JSONObject undo)throws Exception {
        synchronized(ChartLibrary.class){
            new LibraryCatalog(s,p);JSONObject j=new JSONObject().put("songs",s).put("packs",p);
            if(undo!=null)writeJson(new File(root,".practice-catalog-undo.json"),undo);
            writeJson(new File(root,".practice-catalog-transaction.json"),j);recover(root);regenerate(getActivity());
        }
        PracticeOverlay.catalogChanged();ui.post(()->refresh(true));
    }
    public static ChartLibrary attach(Activity a){ChartLibrary f=(ChartLibrary)a.getFragmentManager().findFragmentByTag("practice-library");if(f==null){f=new ChartLibrary();a.getFragmentManager().beginTransaction().add(f,"practice-library").commit();a.getFragmentManager().executePendingTransactions();}return f;}
    @Override public void onCreate(Bundle b){super.onCreate(b);setRetainInstance(true);root=root(getActivity());if(b!=null){selectedPack=b.getString("selectedPack");openedPack=b.getString("openedPack");section=b.getString("section");String zip=b.getString("pendingZip");if(zip!=null)pendingZip=Uri.parse(zip);}}
    @Override public void onSaveInstanceState(Bundle b){super.onSaveInstanceState(b);b.putString("selectedPack",selectedPack);b.putString("openedPack",openedPack);b.putString("section",section);if(pendingZip!=null)b.putString("pendingZip",pendingZip.toString());}
    @Override public void onConfigurationChanged(android.content.res.Configuration config){super.onConfigurationChanged(config);if(page!=null&&page.isShowing())ui.post(()->{layoutPage();refresh(true);});}
    @Override public void onResume(){super.onResume();if(page!=null&&page.isShowing())refresh(true);}
    @Override public void onDestroy(){dismissPage();pictures.shutdownNow();super.onDestroy();}
    private void message(String s){if(getActivity()!=null&&!getActivity().isFinishing())styled(new AlertDialog.Builder(getActivity()).setMessage(s).setPositiveButton("确定",null).show());}
    private void load()throws Exception{prepare(getActivity());songs=json(new File(root,"catalog-songlist.json"));packs=json(new File(root,"catalog-packlist.json"));}
    private int dp(float n){return (int)(getActivity().getResources().getDisplayMetrics().density*n+.5f);}
    private void ensureFont(){if(font!=null)return;for(String n:new String[]{"NotoSansCJKsc-Regular.otf","Exo-Regular.ttf"})try{File f=new File(root,"Fonts/"+n);font=f.exists()?Typeface.createFromFile(f):Typeface.createFromAsset(getActivity().getAssets(),"Fonts/"+n);break;}catch(Exception ignored){}}
    private void applyFont(View v){ensureFont();if(v instanceof TextView&&font!=null)((TextView)v).setTypeface(font);if(v instanceof ViewGroup){ViewGroup g=(ViewGroup)v;for(int i=0;i<g.getChildCount();i++)applyFont(g.getChildAt(i));}}
    private void styled(Dialog d){if(d.getWindow()!=null)applyFont(d.getWindow().getDecorView());}
    private float fontPixels(int size){android.util.DisplayMetrics metrics=getResources().getDisplayMetrics();float heightDp=(pageHeight>0?pageHeight:availableBounds().height())/metrics.density;float scale=Math.min(getResources().getConfiguration().fontScale,Math.max(1f,Math.min(1.35f,heightDp/480f)));return size*metrics.density*scale;}
    private TextView text(String label,int size){TextView t=new TextView(getActivity());t.setText(label);t.setTextColor(0xff33283e);t.setTextSize(android.util.TypedValue.COMPLEX_UNIT_PX,fontPixels(size));t.setGravity(Gravity.CENTER);t.setIncludeFontPadding(true);t.setPadding(dp(8),dp(6),dp(8),dp(6));applyFont(t);return t;}
    private final class CenteredButton extends Button {
        CenteredButton(){super(getActivity());}
        @Override protected void onMeasure(int width,int height){super.onMeasure(width,height);Paint.FontMetricsInt f=getPaint().getFontMetricsInt();int lines=getLayout()==null?f.bottom-f.top:getLayout().getHeight();int needed=LibraryUi.buttonHeight(Math.max(lines,f.bottom-f.top),getPaddingTop()+getPaddingBottom(),dp(44));setMeasuredDimension(getMeasuredWidth(),Math.max(getMeasuredHeight(),needed));}
    }
    private Button button(String label,Runnable action){Button b=new CenteredButton();b.setText(label);b.setAllCaps(false);b.setTextSize(android.util.TypedValue.COMPLEX_UNIT_PX,fontPixels(13));b.setGravity(Gravity.CENTER);b.setIncludeFontPadding(true);b.setMinHeight(0);b.setMinimumHeight(0);b.setMinWidth(0);b.setMinimumWidth(0);b.setPadding(dp(10),dp(8),dp(10),dp(8));b.setMaxLines(3);b.setEllipsize(android.text.TextUtils.TruncateAt.END);applyFont(b);GradientDrawable background=new GradientDrawable();background.setColor(0xffe3dce9);background.setCornerRadius(dp(4));background.setStroke(dp(1),0xffd1c5dd);b.setBackground(background);b.setOnClickListener(v->action.run());return b;}
    private LinearLayout column(){LinearLayout l=new LinearLayout(getActivity());l.setOrientation(1);return l;}
    private LinearLayout row(){LinearLayout l=new LinearLayout(getActivity());l.setGravity(Gravity.CENTER_VERTICAL);return l;}
    private void addAction(GridLayout grid,int index,String name,Runnable r){int columns=grid.getColumnCount();GridLayout.LayoutParams p=new GridLayout.LayoutParams(GridLayout.spec(index/columns),GridLayout.spec(index%columns,1f));p.width=0;p.height=-2;p.setMargins(dp(3),dp(3),dp(3),dp(3));grid.addView(button(name,r),p);}
    private void error(Exception e){android.util.Log.e("ArcPractice","library action failed",e);message("操作失败："+e.getMessage());}
    public void show(){
        if(busy){message("正在导入，请稍候");return;}
        styled(new AlertDialog.Builder(getActivity()).setTitle("谱面与曲包").setItems(new String[]{"从 ZIP 导入新谱面","曲包与分类管理","撤销最近一次曲库修改","一键应用 finale_conflict / dark_vs","一键恢复原背景和轨道"},(d,n)->{
            if(n==0)pick(501,"application/zip");if(n==1){pendingZip=null;openedPack=null;openPage();}if(n==2)undo();if(n>=3)theme(n==3);
        }).show());
    }
    private void theme(boolean on){try{getActivity().getSharedPreferences("practice",0).edit().putBoolean("theme",on).commit();regenerate(getActivity());write(new File(root,"theme-mode"),new byte[]{(byte)(on?1:0)});PracticeOverlay.catalogChanged();message((on?"全曲背景和轨道替换已保存。":"已恢复原背景和轨道。")+"\n返回主界面再进入选曲即可刷新曲库；已缓存的背景贴图需重启游戏更新。");}catch(Exception e){error(e);}}
    private void pick(int code,String type){Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType(type);if(code==501)i.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"application/zip","application/x-zip-compressed","application/octet-stream"});startActivityForResult(i,code);}
    private void choosePack(boolean cover){if(cover){pendingZip=null;}openedPack=null;openPage();}
    private long stamp(){long x=0;for(String n:new String[]{"catalog-songlist.json","catalog-packlist.json","songs/songlist","songs/packlist","songs/pack","songs/pack/1080"}){File f=new File(root,n);x=x*31+f.lastModified();x=x*31+f.length();}return x;}
    private void observe(){
        for(String n:new String[]{"","songs","songs/pack","songs/pack/1080"}){File f=new File(root,n);if(!f.isDirectory())continue;
            FileObserver o=new FileObserver(f.getAbsolutePath(),FileObserver.CLOSE_WRITE|FileObserver.MOVED_TO|FileObserver.DELETE|FileObserver.CREATE){public void onEvent(int event,String path){if(path!=null&&(path.contains("songlist")||path.contains("packlist")||path.endsWith(".png"))){ui.removeCallbacks(check);ui.postDelayed(check,350);}}};o.startWatching();observers.add(o);
        }
    }
    private void dismissPage(){ui.removeCallbacks(check);for(FileObserver o:observers)o.stopWatching();observers.clear();imageCache.evictAll();pageGeneration++;page=null;}
    private Rect availableBounds(){
        Activity activity=getActivity();Rect out=new Rect();activity.getWindow().getDecorView().getWindowVisibleDisplayFrame(out);
        if(Build.VERSION.SDK_INT>=30){WindowMetrics metrics=activity.getWindowManager().getCurrentWindowMetrics();out=new Rect(metrics.getBounds());android.graphics.Insets insets=metrics.getWindowInsets().getInsetsIgnoringVisibility(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());out.inset(insets.left,insets.top,insets.right,insets.bottom);}
        if(out.width()<=0||out.height()<=0)out.set(0,0,getResources().getDisplayMetrics().widthPixels,getResources().getDisplayMetrics().heightPixels);return out;
    }
    private final class HeaderScroll extends ScrollView {
        HeaderScroll(){super(getActivity());setFillViewport(false);setVerticalScrollBarEnabled(true);}
        @Override protected void onMeasure(int width,int height){super.onMeasure(width,View.MeasureSpec.makeMeasureSpec(LibraryUi.headerLimit(pageHeight),View.MeasureSpec.AT_MOST));}
    }
    private void layoutPage(){
        if(page==null)return;Rect bounds=availableBounds();int margin=Math.min(dp(12),Math.min(bounds.width(),bounds.height())/25);pageWidth=Math.max(1,bounds.width()-margin*2);pageHeight=Math.max(1,bounds.height()-margin*2);
        LinearLayout layout=column();layout.setPadding(dp(8),dp(6),dp(8),dp(6));layout.setBackgroundColor(0xfff5f1f8);
        HeaderScroll headerScroll=new HeaderScroll();pageHeader=headerScroll;LinearLayout header=column();LinearLayout top=row();heading=text("曲包",19);top.addView(heading,new LinearLayout.LayoutParams(0,-2,1));
        top.addView(button("返回",()->{if(openedPack!=null){openedPack=null;refresh(true);}else if(page!=null)page.dismiss();}),new LinearLayout.LayoutParams(-2,-2));
        LinearLayout.LayoutParams close=new LinearLayout.LayoutParams(-2,-2);close.setMargins(dp(6),0,0,0);top.addView(button("关闭",()->{pendingZip=null;if(page!=null)page.dismiss();}),close);header.addView(top);
        GridLayout actions=new GridLayout(getActivity());float widthDp=pageWidth/getResources().getDisplayMetrics().density;actions.setColumnCount(LibraryUi.columns(widthDp,getResources().getConfiguration().fontScale));
        addAction(actions,0,"导入谱面",()->pick(501,"application/zip"));addAction(actions,1,"新建曲包",this::createPack);addAction(actions,2,"新建分类",()->newSection(null));addAction(actions,3,"刷新",()->refresh(true));header.addView(actions,new LinearLayout.LayoutParams(-1,-2));
        headerScroll.addView(header);layout.addView(headerScroll,new LinearLayout.LayoutParams(-1,-2));body=row();layout.addView(body,new LinearLayout.LayoutParams(-1,0,1));page.setContentView(layout);
        Window w=page.getWindow();if(w!=null){w.setBackgroundDrawableResource(android.R.color.transparent);w.setGravity(Gravity.CENTER);w.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);w.setLayout(pageWidth,pageHeight);}
        android.util.Log.i("ArcPractice","library viewport="+pageWidth+"x"+pageHeight+" fontScale="+getResources().getConfiguration().fontScale+" toolbarColumns="+actions.getColumnCount());
    }
    private void openPage(){
        if(page!=null&&page.isShowing()){refresh(true);return;}ensureFont();page=new Dialog(getActivity());page.requestWindowFeature(Window.FEATURE_NO_TITLE);page.setOnDismissListener(d->dismissPage());layoutPage();page.show();layoutPage();observe();refresh(true);
    }
    private void refresh(boolean force){
        if(page==null||!page.isShowing())return;if(busy){ui.postDelayed(check,1000);return;}
        try{long now=stamp();if(force||now!=fingerprint){load();fingerprint=stamp();PracticeOverlay.catalogChanged();pageGeneration++;imageCache.evictAll();render();}}catch(Exception e){error(e);}
        ui.removeCallbacks(check);ui.postDelayed(check,1000);
    }
    private void render()throws Exception {
        body.removeAllViews();LibraryCatalog model=new LibraryCatalog(songs,packs);
        if(openedPack!=null&&model.findPack(openedPack)!=null){renderPack(model.findPack(openedPack));return;}openedPack=null;
        LinkedHashMap<String,String> categories=model.sections();if(section==null||!categories.containsKey(section))section=categories.isEmpty()?null:categories.keySet().iterator().next();
        heading.setText(pendingZip==null?"曲包与分类":"选择导入目标曲包");
        LinearLayout side=column();ArrayList<String> ids=new ArrayList<>(categories.keySet());
        for(String id:ids){TextView label=text(categories.get(id),15);label.setMinHeight(dp(48));label.setBackgroundColor(id.equals(section)?0xffded1eb:Color.TRANSPARENT);label.setOnClickListener(v->{section=id;try{render();}catch(Exception e){error(e);}});label.setOnLongClickListener(v->{deleteSection(id);return true;});side.addView(label,new LinearLayout.LayoutParams(-1,-2));}
        side.addView(new Space(getActivity()),new LinearLayout.LayoutParams(1,0,1));side.addView(button("删除当前分类",()->{if(section!=null)deleteSection(section);}),new LinearLayout.LayoutParams(-1,-2));
        ScrollView categoryScroll=new ScrollView(getActivity());categoryScroll.setFillViewport(true);categoryScroll.addView(side);body.addView(categoryScroll,new LinearLayout.LayoutParams(dp(LibraryUi.sidebar(pageWidth/getResources().getDisplayMetrics().density,getResources().getConfiguration().fontScale)),-1));
        ArrayList<JSONObject> list=new ArrayList<>();JSONArray a=packs.getJSONArray("packs");for(int i=0;i<a.length();i++){JSONObject p=a.getJSONObject(i);if(p.optString("section","arcaea").equals(section))list.add(p);}
        GridView grid=new GridView(getActivity());grid.setNumColumns(GridView.AUTO_FIT);grid.setColumnWidth(dp(160));grid.setHorizontalSpacing(dp(12));grid.setVerticalSpacing(dp(10));grid.setStretchMode(GridView.STRETCH_COLUMN_WIDTH);grid.setAdapter(new CoverAdapter(list));
        grid.setOnItemClickListener((p,v,n,id)->{JSONObject pack=list.get(n);selectedPack=pack.optString("id");if(pendingZip!=null){if(page!=null)page.dismiss();importZip();}else{openedPack=selectedPack;try{render();}catch(Exception e){error(e);}}});
        body.addView(grid,new LinearLayout.LayoutParams(0,-1,1));
    }
    private final class TextAdapter extends BaseAdapter {
        final ArrayList<String> labels;final int chosen;TextAdapter(ArrayList<String> l){this(l,-1);}TextAdapter(ArrayList<String> l,int c){labels=l;chosen=c;}public int getCount(){return labels.size();}public Object getItem(int p){return labels.get(p);}public long getItemId(int p){return p;}
        public View getView(int p,View old,ViewGroup parent){TextView v=old instanceof TextView?(TextView)old:text("",15);v.setText(labels.get(p));v.setBackgroundColor(p==chosen?0xffded1eb:Color.TRANSPARENT);v.setMinHeight(dp(48));return v;}
    }
    private final class CoverAdapter extends BaseAdapter {
        final ArrayList<JSONObject> list;CoverAdapter(ArrayList<JSONObject> l){list=l;}public int getCount(){return list.size();}public Object getItem(int p){return list.get(p);}public long getItemId(int p){return p;}
        public View getView(int n,View old,ViewGroup parent){LinearLayout card;ImageView image;TextView name;
            if(old instanceof LinearLayout){card=(LinearLayout)old;image=(ImageView)card.getChildAt(0);name=(TextView)card.getChildAt(1);}else{card=column();image=new CoverView();image.setScaleType(ImageView.ScaleType.FIT_CENTER);image.setBackgroundColor(0xffd9cfe4);card.addView(image,new LinearLayout.LayoutParams(-1,-2));name=text("",14);name.setGravity(Gravity.CENTER);name.setMaxLines(2);name.setIncludeFontPadding(true);name.setEllipsize(android.text.TextUtils.TruncateAt.END);card.addView(name,new LinearLayout.LayoutParams(-1,-2));}
            JSONObject pack=list.get(n);name.setText(LibraryCatalog.title(pack).replaceAll("[\\t ]+"," ").replaceAll("\\s*\\n\\s*","\n").trim());image.setContentDescription(LibraryCatalog.title(pack));loadCover(image,pack);return card;
        }
    }
    private final class CoverView extends ImageView {
        float ratio=717f/403f;CoverView(){super(getActivity());}
        @Override protected void onMeasure(int width,int height){int w=View.MeasureSpec.getSize(width);Paint label=new Paint();label.setTypeface(font);label.setTextSize(fontPixels(14));Paint.FontMetricsInt f=label.getFontMetricsInt();int caption=(f.bottom-f.top)*2+dp(12);int header=pageHeader==null?dp(96):pageHeader.getMeasuredHeight();int available=pageHeight-header-dp(16)-caption;int h=Math.min(Math.round(w*ratio),Math.max(dp(72),available));super.onMeasure(width,View.MeasureSpec.makeMeasureSpec(h,View.MeasureSpec.EXACTLY));}
    }
    private void bindCover(ImageView view,Bitmap bitmap){if(view instanceof CoverView){((CoverView)view).ratio=bitmap.getHeight()/(float)bitmap.getWidth();view.requestLayout();}view.setImageBitmap(bitmap);}
    private InputStream resource(String path)throws IOException {File file=new File(root,path);if(file.isFile())return new FileInputStream(file);return getActivity().getAssets().open(path);}
    private ArrayList<String> coverPaths(JSONObject p){String id=p.optString("id"),img=p.optString("img","");ArrayList<String> out=new ArrayList<>();if(!img.isEmpty()&&!img.contains("..")&&!img.contains("/")){out.add("songs/pack/"+img);out.add("songs/pack/1080_"+img);}out.add("songs/pack/1080_select_"+id+".png");out.add("songs/pack/select_"+id+".png");String parent=p.optString("pack_parent","");if(!parent.isEmpty()&&!parent.contains("/"))out.add("songs/pack/1080_select_"+parent+".png");return out;}
    private void loadCover(ImageView view,JSONObject pack){
        final String key=pack.optString("id")+":"+fingerprint;view.setTag(key);view.setImageDrawable(null);if(view instanceof CoverView)((CoverView)view).ratio=717f/403f;Bitmap cached=imageCache.get(key);if(cached!=null){bindCover(view,cached);return;}
        final int generation=pageGeneration;final ArrayList<String> paths=coverPaths(pack);
        pictures.execute(()->{Bitmap bitmap=null;for(String path:paths)try(InputStream in=resource(path)){BitmapFactory.Options options=new BitmapFactory.Options();options.inSampleSize=2;bitmap=BitmapFactory.decodeStream(in,null,options);if(bitmap!=null)break;}catch(Exception ignored){}
            final Bitmap result=bitmap;if(result!=null)ui.post(()->{if(generation==pageGeneration&&page!=null){imageCache.put(key,result);if(key.equals(view.getTag()))bindCover(view,result);}else result.recycle();});
        });
    }
    private void renderPack(JSONObject pack)throws Exception {
        String id=pack.getString("id");heading.setText(LibraryCatalog.title(pack));LinearLayout detail=column();detail.setPadding(dp(6),0,dp(8),0);int detailWidth=dp(LibraryUi.sidebar(pageWidth/getResources().getDisplayMetrics().density,getResources().getConfiguration().fontScale));
        ImageView image=new ImageView(getActivity());image.setScaleType(ImageView.ScaleType.FIT_CENTER);detail.addView(image,new LinearLayout.LayoutParams(-1,Math.max(dp(100),Math.round(detailWidth*1.5f))));loadCover(image,pack);
        detail.addView(button("更换封面",()->{selectedPack=id;pick(502,"image/*");}));detail.addView(button("移动至分类",()->movePack(id)));detail.addView(button("删除曲包",()->deletePack(id)));ScrollView detailScroll=new ScrollView(getActivity());detailScroll.addView(detail);body.addView(detailScroll,new LinearLayout.LayoutParams(detailWidth,-1));
        Set<String> family=new LibraryCatalog(songs,packs).descendants(id);JSONArray a=songs.getJSONArray("songs");ArrayList<JSONObject> tracks=new ArrayList<>();ArrayList<String> labels=new ArrayList<>();
        for(int i=0;i<a.length();i++){JSONObject song=a.getJSONObject(i);if(family.contains(song.optString("set","base"))){tracks.add(song);labels.add(LibraryCatalog.title(song)+"\n"+song.optString("artist","")+"  ·  "+song.optString("id"));}}
        LinearLayout right=column();right.addView(text(tracks.size()+" 首歌曲 · 点击歌曲进行管理",14));ListView list=new ListView(getActivity());list.setAdapter(new TextAdapter(labels));list.setOnItemClickListener((p,v,n,key)->songActions(tracks.get(n)));right.addView(list,new LinearLayout.LayoutParams(-1,0,1));body.addView(right,new LinearLayout.LayoutParams(0,-1,1));
    }
    private void songActions(JSONObject song){String id=song.optString("id");styled(new AlertDialog.Builder(getActivity()).setTitle(LibraryCatalog.title(song)).setItems(new String[]{"删除歌曲","移动到其他曲包"},(d,n)->{if(n==0)styled(new AlertDialog.Builder(getActivity()).setTitle("删除歌曲？").setMessage("将从曲库列表移除该歌曲。资源保留，可在入口撤销最近一次修改。").setNegativeButton("取消",null).setPositiveButton("删除",(x,y)->{try{mutate(m->m.deleteSong(id));}catch(Exception e){error(e);}}).show());else moveSong(id);}).show());}
    private void deletePack(String id){try{load();LibraryCatalog m=new LibraryCatalog(songs,packs);Set<String> ids=m.descendants(id);int count=m.songCount(ids);styled(new AlertDialog.Builder(getActivity()).setTitle("删除曲包").setMessage("包含 "+ids.size()+" 个曲包（含子曲包）、"+count+" 首歌曲。可撤销最近一次修改。").setNeutralButton("取消",null).setNegativeButton("保留歌曲并移至其他曲包",(d,n)->deletePacksNow(id,false)).setPositiveButton("连同歌曲删除",(d,n)->deletePacksNow(id,true)).show());}catch(Exception e){error(e);}}
    private void deletePacksNow(String id,boolean songsToo){try{mutate(m->m.deletePacks(m.descendants(id),songsToo));openedPack=null;refresh(true);}catch(Exception e){error(e);}}
    private void deleteSection(String id){styled(new AlertDialog.Builder(getActivity()).setTitle("删除分类？").setMessage("可以保留曲包并移至其他分类，或将分类内的曲包和歌曲一同从列表删除。可撤销最近一次修改。").setNeutralButton("取消",null).setNegativeButton("保留曲包",(d,n)->deleteSectionNow(id,false)).setPositiveButton("连同曲包和歌曲删除",(d,n)->deleteSectionNow(id,true)).show());}
    private void deleteSectionNow(String id,boolean contents){try{mutate(m->m.deleteSection(id,contents));section=null;refresh(true);}catch(Exception e){error(e);}}
    private interface SectionChoice {void selected(String id)throws Exception;}
    private void selectSection(SectionChoice action){try{load();LinkedHashMap<String,String> sections=new LibraryCatalog(songs,packs).sections();ArrayList<String> ids=new ArrayList<>(sections.keySet()),names=new ArrayList<>(sections.values());names.add("＋ 创建新分类");styled(new AlertDialog.Builder(getActivity()).setTitle("选择曲包分类").setItems(names.toArray(new String[0]),(d,n)->{if(n==ids.size())newSection(action);else try{action.selected(ids.get(n));}catch(Exception e){error(e);}}).show());}catch(Exception e){error(e);}}
    private EditText nameInput(String hint){EditText e=new EditText(getActivity());e.setSingleLine(true);e.setHint(hint);e.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(80)});applyFont(e);return e;}
    private void newSection(SectionChoice next){EditText name=nameInput("分类名称");AlertDialog d=new AlertDialog.Builder(getActivity()).setTitle("新建分类").setView(name).setNegativeButton("取消",null).setPositiveButton("创建",null).create();d.show();styled(d);d.getButton(-1).setOnClickListener(v->{try{String label=name.getText().toString().trim();if(label.isEmpty())throw new IOException("分类名称不能为空");final String[] id={null};mutate(m->id[0]=m.addSection(label));section=id[0];d.dismiss();if(next!=null)next.selected(id[0]);else refresh(true);}catch(Exception e){error(e);}});}
    private void createPack(){selectSection(category->{EditText name=nameInput("曲包名称");AlertDialog d=new AlertDialog.Builder(getActivity()).setTitle("新建曲包").setView(name).setNegativeButton("取消",null).setPositiveButton("创建",null).create();d.show();styled(d);d.getButton(-1).setOnClickListener(v->{try{String title=name.getText().toString().trim();if(title.isEmpty())throw new IOException("曲包名称不能为空");String id="custom_"+UUID.randomUUID().toString().replace("-","");mutate(m->m.packs.getJSONArray("packs").put(LibraryCatalog.newPack(id,title,category)));selectedPack=id;section=category;d.dismiss();if(pendingZip!=null){if(page!=null)page.dismiss();importZip();}else{openedPack=id;refresh(true);message("曲包已创建并生成默认封面。导入谱面后，返回主界面再进入选曲，可在对应难度下找到曲包入口。");}}catch(Exception e){error(e);}});});}
    private void movePack(String id){selectSection(category->{mutate(m->{for(String child:m.descendants(id))m.findPack(child).put("section",category);});section=category;refresh(true);});}
    private void moveSong(String id){try{load();JSONArray a=packs.getJSONArray("packs");String[] names=new String[a.length()];for(int i=0;i<names.length;i++)names[i]=LibraryCatalog.title(a.getJSONObject(i));styled(new AlertDialog.Builder(getActivity()).setTitle("选择目标曲包").setItems(names,(d,n)->{try{String target=a.getJSONObject(n).getString("id");mutate(m->{if(m.findPack(target)==null)throw new IOException("目标曲包已删除");JSONArray tracks=m.songs.getJSONArray("songs");for(int i=0;i<tracks.length();i++)if(tracks.getJSONObject(i).optString("id").equals(id))tracks.getJSONObject(i).put("set",target);});}catch(Exception e){error(e);}}).show());}catch(Exception e){error(e);}}
    private void undo(){try{File f=new File(root,".practice-catalog-undo.json");if(!f.isFile())throw new IOException("暂无可撤销的曲库修改");JSONObject j=json(f);commit(j.getJSONObject("songs"),j.getJSONObject("packs"),null);f.delete();message("已恢复最近一次修改前的曲库列表。");}catch(Exception e){error(e);}}
    private int[] coverSize(JSONObject pack){BitmapFactory.Options options=new BitmapFactory.Options();options.inJustDecodeBounds=true;for(String path:coverPaths(pack))try(InputStream in=resource(path)){BitmapFactory.decodeStream(in,null,options);if(options.outWidth>0&&options.outHeight>0&&options.outWidth<=2048&&options.outHeight<=4096)return new int[]{options.outWidth,options.outHeight};}catch(Exception ignored){}return new int[]{403,717};}
    private void saveCover(byte[] bytes,String id)throws Exception {
        if(!PackCovers.safeId(id))throw new IOException("曲包 ID 无效，请重新选择曲包");load();JSONObject p=new LibraryCatalog(songs,packs).findPack(id);if(p==null)throw new IOException("曲包已删除");int[] size=coverSize(p);BitmapFactory.Options options=new BitmapFactory.Options();options.inJustDecodeBounds=true;BitmapFactory.decodeByteArray(bytes,0,bytes.length,options);
        if(options.outWidth<=0||options.outHeight<=0||options.outWidth>16384||options.outHeight>16384)throw new IOException("封面图片无效或超过 16384 像素");options.inJustDecodeBounds=false;options.inSampleSize=Math.max(1,Math.max(options.outWidth,options.outHeight)/2048);
        Bitmap input=BitmapFactory.decodeByteArray(bytes,0,bytes.length,options);if(input==null)throw new IOException("无法解码封面");Bitmap output=Bitmap.createBitmap(size[0],size[1],Bitmap.Config.ARGB_8888);float[] r=LibraryCatalog.coverRect(input.getWidth(),input.getHeight(),size[0],size[1]);new Canvas(output).drawBitmap(input,null,new RectF(r[0],r[1],r[2],r[3]),new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG));
        ByteArrayOutputStream out=new ByteArrayOutputStream();output.compress(Bitmap.CompressFormat.PNG,100,out);input.recycle();output.recycle();String name="select_"+id+"_"+Long.toHexString(System.currentTimeMillis())+".png";
        write(new File(root,"songs/pack/1080_"+name),out.toByteArray());write(new File(root,"songs/pack/"+name),out.toByteArray());PackCovers.aliases(root,id,out.toByteArray());
        mutate(m->{JSONObject pack=m.findPack(id);if(pack==null)throw new IOException("曲包已删除");pack.put("img",name).put("custom_banner",false).put("cutout_pack_image",false);});
    }
    @Override public void onActivityResult(int request,int result,Intent data){
        if(result!=Activity.RESULT_OK||data==null)return;try{int flags=data.getFlags()&Intent.FLAG_GRANT_READ_URI_PERMISSION;if(flags!=0)getActivity().getContentResolver().takePersistableUriPermission(data.getData(),flags);}catch(SecurityException ignored){}if(request==501){pendingZip=data.getData();choosePack(false);}
        if(request==502){final Activity activity=getActivity();final Uri uri=data.getData();final String pack=selectedPack;busy=true;new Thread(()->{try{saveCover(read(activity.getContentResolver().openInputStream(uri)),pack);activity.runOnUiThread(()->{refresh(true);message("封面已按原曲包比例适配并保存。");});}catch(Exception e){activity.runOnUiThread(()->error(e));}finally{busy=false;ui.post(()->refresh(true));}},"pack-cover").start();}
    }
    private static void saveImage(byte[] b,File f,boolean jpeg)throws Exception{BitmapFactory.Options o=new BitmapFactory.Options();o.inJustDecodeBounds=true;BitmapFactory.decodeByteArray(b,0,b.length,o);if(o.outWidth<=0||o.outHeight<=0||o.outWidth>8192||o.outHeight>8192)throw new IOException("曲绘或封面不是有效图片（最大 8192 像素）");o.inJustDecodeBounds=false;o.inSampleSize=Math.max(1,Math.max(o.outWidth,o.outHeight)/2048);Bitmap image=BitmapFactory.decodeByteArray(b,0,b.length,o);if(image==null)throw new IOException("图片解码失败");ByteArrayOutputStream out=new ByteArrayOutputStream();image.compress(jpeg?Bitmap.CompressFormat.JPEG:Bitmap.CompressFormat.PNG,95,out);image.recycle();write(f,out.toByteArray());}
    private static void saveThumbnail(byte[] bytes,File file)throws Exception {
      Bitmap image=BitmapFactory.decodeByteArray(bytes,0,bytes.length);if(image==null)throw new IOException("曲绘无法解码");
      Bitmap small=Bitmap.createScaledBitmap(image,256,256,true);
      ByteArrayOutputStream out=new ByteArrayOutputStream();small.compress(Bitmap.CompressFormat.JPEG,95,out);
      if(small!=image)small.recycle();image.recycle();write(file,out.toByteArray());
    }
    private void importZip(){busy=true;Activity a=getActivity();Uri uri=pendingZip;String pack=selectedPack;new Thread(()->{File stage=null;try{
      ChartArchive.Contents contents=ChartArchive.load(a.getContentResolver().openInputStream(uri));
      TreeMap<Integer,byte[]> charts=contents.charts;byte[] music=contents.music,jacket=contents.jacket;JSONObject metadata=contents.metadata;
      ChartMetadata.validateBackgrounds(metadata,ChartMetadata.backgrounds(new File(root,"img/bg/1080")));
      String id="local_"+UUID.randomUUID().toString().replace("-","");stage=new File(root,".stage-"+id);stage.mkdirs();for(Map.Entry<Integer,byte[]> e:charts.entrySet())write(new File(stage,e.getKey()+".aff"),e.getValue());write(new File(stage,"base.ogg"),music);saveImage(jacket,new File(stage,"base.jpg"),true);saveImage(jacket,new File(stage,"1080_base.jpg"),true);
      JSONObject song=new JSONObject(metadata.toString());song.put("idx",songs.getJSONArray("songs").length()+10000).put("id",id).put("title_localized",metadata.optJSONObject("title_localized")!=null?metadata.getJSONObject("title_localized"):new JSONObject().put("en",metadata.optString("title","Imported chart"))).put("artist",metadata.optString("artist","")).put("bpm",metadata.optString("bpm","120")).put("bpm_base",metadata.optDouble("bpm_base",120)).put("set",pack).put("purchase","").put("side",metadata.optInt("side",0)).put("bg",metadata.optString("bg","base_light")).put("audioPreview",metadata.optInt("audioPreview",0)).put("audioPreviewEnd",metadata.optInt("audioPreviewEnd",15000)).put("date",System.currentTimeMillis()/1000).put("version","1.0");JSONArray diffs=new JSONArray();for(int c:charts.keySet())diffs.put(ChartArchive.difficulty(metadata,c));song.put("difficulties",diffs);
      int nextIdx=0;JSONArray existing=songs.getJSONArray("songs");for(int i=0;i<existing.length();i++)nextIdx=Math.max(nextIdx,existing.getJSONObject(i).optInt("idx",i)+1);song.put("idx",nextIdx);
      for(int i=0;i<diffs.length();i++)ChartMetadata.credits(song,diffs.getJSONObject(i));
      saveThumbnail(contents.thumbnail==null?jacket:contents.thumbnail,new File(stage,"1080_base_256.jpg"));
      write(new File(stage,"base_256.jpg"),read(new FileInputStream(new File(stage,"1080_base_256.jpg"))));
      for(int c:charts.keySet())if(diffs.getJSONObject(new ArrayList<Integer>(charts.keySet()).indexOf(c)).optBoolean("jacketOverride",false)){
        write(new File(stage,"1080_"+c+".jpg"),read(new FileInputStream(new File(stage,"1080_base.jpg"))));
        write(new File(stage,"1080_"+c+"_256.jpg"),read(new FileInputStream(new File(stage,"1080_base_256.jpg"))));
      }
      File dest=new File(root,"songs/"+id);dest.getParentFile().mkdirs();if(!stage.renameTo(dest))throw new IOException("无法写入曲目目录");mutate(model->{if(model.findPack(pack)==null)throw new IOException("目标曲包已删除");int index=0;JSONArray tracks=model.songs.getJSONArray("songs");for(int i=0;i<tracks.length();i++)index=Math.max(index,tracks.getJSONObject(i).optInt("idx",i)+1);song.put("idx",index);tracks.put(song);});android.util.Log.i("ArcPractice","ZIP imported title="+metadata.optString("title",metadata.optJSONObject("title_localized")==null?"Imported chart":metadata.optJSONObject("title_localized").optString("en"))+" difficulties="+charts.keySet());a.runOnUiThread(()->message("谱面已导入，可在曲包页面立即查看。\n返回主界面再进入选曲即可刷新游戏曲库。"));
    }catch(Exception e){android.util.Log.e("ArcPractice","ZIP import failed",e);a.runOnUiThread(()->message("导入失败："+e.getMessage()));}finally{busy=false;if(stage!=null&&stage.exists()){File[] fs=stage.listFiles();if(fs!=null)for(File f:fs)f.delete();stage.delete();}}},"chart-import").start();}
}
