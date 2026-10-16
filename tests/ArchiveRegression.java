package moe.practice;
import java.io.*;
import java.util.zip.*;
import android.graphics.BitmapFactory;
public class ArchiveRegression {
 public static void main(String[] args)throws Exception {
  long start=System.nanoTime();ChartArchive.Contents c=ChartArchive.load(new FileInputStream(args[0]));
  if(c.charts.size()!=1||!c.charts.containsKey(3))throw new AssertionError("difficulty");
  if(!c.metadata.getJSONObject("title_localized").getString("en").equals("Bismuth"))throw new AssertionError("metadata");
  String aff=new String(c.charts.get(3),"UTF-8");if(aff.indexOf('\r')>=0)throw new AssertionError("CRLF normalization");
  BitmapFactory.Options bounds=new BitmapFactory.Options();bounds.inJustDecodeBounds=true;BitmapFactory.decodeByteArray(c.jacket,0,c.jacket.length,bounds);if(bounds.outWidth<=0)throw new AssertionError("jacket");
  for(String newline:new String[]{"\n","\r\n","\r"}){
   String sample="\uFEFFAudioOffset:0"+newline+"  -  "+newline+"timing (0,120,4);"+newline+"// ignore unmatched ( in comments"+newline+"camera(100,0,0,0,0,0,0,l,100);";
   ChartFormat.validate(sample);ChartFormat.validate(ChartFormat.decode(sample.getBytes("UTF-16")));
  }
  String[] bad={"hello","AudioOffset:0\n-\n(100,1);","AudioOffset:0\n-\ntiming(0,120,4);\n(100,1;","AudioOffset:0\n-\ntiming(0,120,4);\n(100,1));"};
  for(String sample:bad){try{ChartFormat.validate(sample);throw new AssertionError("accepted bad AFF");}catch(IOException expected){}}
  System.out.println("PASS Android ZIP pipeline: 3.aff, Bismuth metadata, OGG, "+bounds.outWidth+"x"+bounds.outHeight+" jacket; newline/BOM/comment regressions; elapsed_ms="+(System.nanoTime()-start)/1000000);
 }
}
