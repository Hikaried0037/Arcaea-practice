package moe.practice;

import android.content.Context;
import android.graphics.*;
import android.text.*;
import org.json.*;
import java.io.*;

/** Keep native pack artwork and the library view on the same revisioned file. */
final class PackCovers {
    static boolean safeId(String id){return id!=null&&id.matches("[A-Za-z0-9_-]{1,128}");}
    static boolean safeFile(String name){return name!=null&&name.matches("[A-Za-z0-9_.-]{1,240}")&&!name.contains("..");}
    static boolean custom(String id){return id.startsWith("custom_")||id.equals("practice_unfiled");}
    static boolean managed(JSONObject pack){String id=pack.optString("id"),img=pack.optString("img");return custom(id)||img.startsWith("select_"+id+"_")||img.startsWith("practice_"+id+"_");}
    static String manifest(JSONObject packs)throws JSONException {
        StringBuilder out=new StringBuilder();JSONArray list=packs.getJSONArray("packs");
        for(int i=0;i<list.length();i++){JSONObject pack=list.getJSONObject(i);String id=pack.optString("id"),name=pack.optString("img");
            if(managed(pack)&&safeId(id)&&safeFile(name))out.append(id).append('\t').append("songs/pack/").append(name).append('\n');
        }
        return out.toString();
    }
    static boolean ensure(Context context,File root,JSONObject packs)throws Exception {
        boolean changed=false;JSONArray list=packs.getJSONArray("packs");
        for(int i=0;i<list.length();i++){
            JSONObject pack=list.getJSONObject(i);String id=pack.optString("id"),name=pack.optString("img");if(!safeId(id)||!managed(pack))continue;
            File image=safeFile(name)?new File(root,"songs/pack/"+name):null;
            if(image==null||!image.isFile()){
                if(!custom(id))continue;
                // Migrate covers saved by earlier plugin versions before generating a placeholder.
                File legacy=new File(root,"songs/pack/1080_select_"+id+".png");
                name="practice_"+id+"_default.png";image=new File(root,"songs/pack/"+name);
                if(legacy.isFile())ChartLibrary.write(image,ChartLibrary.read(new FileInputStream(legacy)));
                else ChartLibrary.write(image,placeholder(context,root,LibraryCatalog.title(pack)));
                pack.put("img",name).put("custom_banner",false).put("cutout_pack_image",false);changed=true;
            }
            boolean needsCopy=false;
            for(String prefix:new String[]{"songs/pack/select_","songs/pack/1080_select_","songs/pack/1080/select_"}){File alias=new File(root,prefix+id+".png");if(!alias.isFile()||alias.length()!=image.length()||alias.lastModified()<image.lastModified())needsCopy=true;}
            if(needsCopy)aliases(root,id,ChartLibrary.read(new FileInputStream(image)));
        }
        ChartLibrary.write(new File(root,".practice-pack-covers.tsv"),manifest(packs).getBytes("UTF-8"));return changed;
    }
    static void aliases(File root,String id,byte[] bytes)throws IOException {
        if(!safeId(id))throw new IOException("曲包 ID 包含不支持的路径字符");
        for(String path:new String[]{"songs/pack/select_","songs/pack/1080_select_","songs/pack/1080/select_"})ChartLibrary.write(new File(root,path+id+".png"),bytes);
    }
    private static byte[] placeholder(Context context,File root,String title)throws Exception {
        Bitmap image=Bitmap.createBitmap(403,717,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(image);Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setShader(new LinearGradient(0,0,403,717,0xff211c37,0xff847399,Shader.TileMode.CLAMP));c.drawRect(0,0,403,717,p);p.setShader(null);
        p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(2);p.setColor(0xffb8a7cd);c.drawRect(18,18,385,699,p);
        c.save();c.rotate(45,201.5f,245);c.drawRect(118,161.5f,285,328.5f,p);c.restore();
        p.setStyle(Paint.Style.FILL);p.setColor(0x5570638b);c.drawRect(19,432,384,698,p);
        TextPaint text=new TextPaint(Paint.ANTI_ALIAS_FLAG);text.setColor(Color.WHITE);text.setTextSize(30);
        for(String font:new String[]{"NotoSansCJKsc-Regular.otf","Exo-Regular.ttf"})try{File f=new File(root,"Fonts/"+font);text.setTypeface(f.isFile()?Typeface.createFromFile(f):Typeface.createFromAsset(context.getAssets(),"Fonts/"+font));break;}catch(Exception ignored){}
        StaticLayout layout=StaticLayout.Builder.obtain(title,0,title.length(),text,343).setAlignment(Layout.Alignment.ALIGN_CENTER).setIncludePad(true).setMaxLines(4).setEllipsize(TextUtils.TruncateAt.END).build();
        c.save();c.translate(30,470+(180-layout.getHeight())/2f);layout.draw(c);c.restore();
        ByteArrayOutputStream out=new ByteArrayOutputStream();image.compress(Bitmap.CompressFormat.PNG,100,out);image.recycle();return out.toByteArray();
    }
}
