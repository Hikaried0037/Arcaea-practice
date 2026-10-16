package moe.practice;
import android.graphics.*;
import org.json.*;
import java.io.*;
public final class PackCoverRegression {
    static int checks;static void check(boolean value,String name){checks++;if(!value)throw new AssertionError(name);}
    public static void main(String[] args)throws Exception {
        File root=new File(args[0]);root.mkdirs();
        JSONObject normal=LibraryCatalog.newPack("custom_default","默认封面测试","arcaea"),uploaded=LibraryCatalog.newPack("custom_upload","上传封面","arcaea").put("img","select_custom_upload_revision.png");
        JSONObject official=new JSONObject().put("id","base").put("section","arcaea");
        Bitmap bitmap=Bitmap.createBitmap(403,717,Bitmap.Config.ARGB_8888);bitmap.eraseColor(Color.BLUE);ByteArrayOutputStream buffer=new ByteArrayOutputStream();bitmap.compress(Bitmap.CompressFormat.PNG,100,buffer);bitmap.recycle();
        ChartLibrary.write(new File(root,"songs/pack/select_custom_upload_revision.png"),buffer.toByteArray());
        JSONObject packs=new JSONObject().put("packs",new JSONArray().put(normal).put(uploaded).put(official));
        check(PackCovers.ensure(null,root,packs),"missing custom cover gets a default");
        check(normal.getString("img").equals("practice_custom_default_default.png"),"default reference is persisted");
        check(!official.has("img"),"original pack metadata remains untouched");
        check(uploaded.getString("img").equals("select_custom_upload_revision.png"),"existing uploaded revision is retained");
        for(String prefix:new String[]{"songs/pack/select_","songs/pack/1080_select_","songs/pack/1080/select_"}){
            File image=new File(root,prefix+"custom_upload.png");check(image.isFile(),"native compatibility path exists");Bitmap decoded=BitmapFactory.decodeFile(image.getAbsolutePath());check(decoded.getWidth()==403&&decoded.getHeight()==717,"native alias dimensions");check(decoded.getPixel(0,0)==Color.BLUE,"alias content correct");decoded.recycle();
        }
        String manifest=new String(ChartLibrary.read(new FileInputStream(new File(root,".practice-pack-covers.tsv"))),"UTF-8");
        check(manifest.contains("custom_upload\tsongs/pack/select_custom_upload_revision.png\n"),"native cover map uses revisioned path");
        check(!manifest.contains("base\t"),"unmodified official artwork falls back to game");
        check(!PackCovers.ensure(null,root,packs),"migration is idempotent");
        check(!PackCovers.safeId("../base")&&!PackCovers.safeFile("../cover.png"),"unsafe paths rejected");
        Bitmap placeholder=BitmapFactory.decodeFile(new File(root,"songs/pack/"+normal.getString("img")).getAbsolutePath());check(placeholder.getWidth()==403&&placeholder.getHeight()==717,"default matches native pack shape");placeholder.recycle();
        for(float width:new float[]{240,320,360,640,800,1280})for(float font:new float[]{1,1.3f,1.5f,2}){
            int columns=LibraryUi.columns(width,font);check(columns>=1&&columns<=4,"toolbar adapts to width and font");int sidebar=LibraryUi.sidebar(width,font);check(sidebar<=width*.37f,"sidebar leaves room for content");
        }
        check(LibraryUi.buttonHeight(70,20,44)==90,"large font is not constrained by old fixed height");
        System.out.println("PackCoverRegression PASS checks="+checks);
    }
}
