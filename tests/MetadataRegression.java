package moe.practice;
import java.io.*;
import java.util.*;
import org.json.*;
import android.graphics.BitmapFactory;
public class MetadataRegression {
 public static void main(String[] args)throws Exception {
  ChartArchive.Contents c=ChartArchive.load(new FileInputStream(args[0]));
  Set<String> bgs=new HashSet<>(Arrays.asList("apophenia","base_light","finale_conflict"));
  ChartMetadata.validateBackgrounds(c.metadata,bgs);
  JSONObject diff=ChartArchive.difficulty(c.metadata,3);ChartMetadata.credits(c.metadata,diff);
  if(!c.metadata.getString("artist").equals("Ludicin")||!diff.getString("artist").equals("Ludicin"))throw new AssertionError("artist lost");
  if(!diff.getString("chartDesigner").isEmpty())throw new AssertionError("invented designer");
  BitmapFactory.Options o=new BitmapFactory.Options();o.inJustDecodeBounds=true;
  BitmapFactory.decodeByteArray(c.thumbnail,0,c.thumbnail.length,o);
  if(o.outWidth<=0||o.outHeight<=0||c.thumbnail==c.jacket)throw new AssertionError("archive thumbnail ignored");
  try(java.util.zip.ZipFile z=new java.util.zip.ZipFile(args[0])){
   java.util.zip.CRC32 crc=new java.util.zip.CRC32();crc.update(c.thumbnail);
   if(crc.getValue()!=z.getEntry("base_256.jpg").getCrc())throw new AssertionError("wrong thumbnail selected");
  }
  JSONObject named=new JSONObject("{\"artist\":\"Composer\",\"chartDesigner\":\"Charter\"}");
  JSONObject d=new JSONObject();ChartMetadata.credits(named,d);
  if(!d.getString("chartDesigner").equals("Charter"))throw new AssertionError("designer lost");
  if(!ChartArchive.difficulty(new JSONObject(),2).getString("chartDesigner").isEmpty())throw new AssertionError("invented missing designer");
  java.lang.reflect.Method thumbnail=ChartLibrary.class.getDeclaredMethod("saveThumbnail",byte[].class,File.class);thumbnail.setAccessible(true);
  File output=new File("/data/local/tmp/arcaea-r4-thumbnail.jpg");thumbnail.invoke(null,c.thumbnail,output);
  BitmapFactory.decodeFile(output.getAbsolutePath(),o);
  if(o.outWidth!=256||o.outHeight!=256)throw new AssertionError("wrong installed thumbnail size");
  output.delete();
  for(String json:new String[]{"{\"bg\":\"missing\"}","{\"bg\":\"apophenia\",\"difficulties\":[{\"ratingClass\":3,\"bg\":\"missing\"}]}","{\"bg_inverse\":\"../x\"}"}){
   try{ChartMetadata.validateBackgrounds(new JSONObject(json),bgs);throw new AssertionError("invalid background accepted");}catch(IOException expected){}
  }
  System.out.println("PASS: existing credits preserved, missing chartDesigner stays empty, base_256 selected, invalid song/difficulty backgrounds rejected");
 }
}
