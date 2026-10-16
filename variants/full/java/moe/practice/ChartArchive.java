package moe.practice;
import java.io.*;
import java.util.*;
import java.util.zip.*;
import org.json.*;

final class ChartArchive {
    static final class Contents {
        final TreeMap<Integer,byte[]> charts=new TreeMap<>();
        byte[] jacket,thumbnail,music;
        JSONObject metadata=new JSONObject();
    }
    static Contents load(InputStream input)throws Exception {
        LinkedHashMap<String,byte[]> files=new LinkedHashMap<>();long total=0;
        try(ZipInputStream zip=new ZipInputStream(input)){ZipEntry entry;byte[] buffer=new byte[32768];int entries=0;
            while((entry=zip.getNextEntry())!=null){
                if(++entries>128)throw new IOException("ZIP 文件数量超过 128");
                String path=entry.getName().replace('\\','/');
                if(path.startsWith("/")||path.contains("../")||path.contains(":"))throw new IOException("ZIP 包含不安全路径");
                if(entry.isDirectory()||path.startsWith("__MACOSX/"))continue;
                String name=path.substring(path.lastIndexOf('/')+1).toLowerCase(Locale.ROOT);if(name.startsWith("."))continue;
                ByteArrayOutputStream out=new ByteArrayOutputStream();int n;
                while((n=zip.read(buffer))!=-1){total+=n;if(total>256L*1024*1024||out.size()+n>128*1024*1024)throw new IOException("ZIP 解压大小超出限制");out.write(buffer,0,n);}
                if(files.put(name,out.toByteArray())!=null)throw new IOException("ZIP 含重复文件名；一次只能导入一首曲目");
            }
        }
        Contents result=new Contents();int affCount=0;for(String name:files.keySet())if(name.endsWith(".aff"))affCount++;
        for(Map.Entry<String,byte[]> file:files.entrySet()){
            String name=file.getKey();if(!name.endsWith(".aff"))continue;
            int difficulty=name.matches("[0-4]\\.aff")?name.charAt(0)-'0':affCount==1?2:-1;
            if(difficulty<0)throw new IOException("多难度 AFF 必须命名 0.aff 至 4.aff");
            try{String chart=ChartFormat.decode(file.getValue());ChartFormat.validate(chart);result.charts.put(difficulty,chart.getBytes("UTF-8"));}
            catch(IOException e){throw new IOException(name+"："+e.getMessage(),e);}
        }
        result.jacket=pick(files,new String[]{"base.jpg","base.png","jacket.jpg","jacket.png","cover.jpg","cover.png"},true);
        for(String name:new String[]{"base_256.jpg","base_256.png","1080_base_256.jpg","1080_base_256.png"})if(files.containsKey(name)){result.thumbnail=files.get(name);break;}
        result.music=pick(files,new String[]{"base.ogg","audio.ogg","music.ogg"},false);
        for(String name:new String[]{"song.json","songlist.json","songlist"})if(files.containsKey(name)){
            JSONObject metadata=new JSONObject(ChartFormat.decode(files.get(name)));
            JSONArray songs=metadata.optJSONArray("songs");
            if(songs!=null){if(songs.length()!=1)throw new IOException("ZIP 元数据必须只包含一首曲目");metadata=songs.getJSONObject(0);}
            result.metadata=metadata;break;
        }
        if(result.charts.isEmpty()||result.jacket==null||result.music==null)throw new IOException("ZIP 必须包含 AFF、曲绘 JPG/PNG 和音乐 OGG");
        byte[] music=result.music;if(music.length<4||music[0]!='O'||music[1]!='g'||music[2]!='g'||music[3]!='S')throw new IOException("音乐必须是有效 OGG，不能只修改扩展名");
        return result;
    }
    private static byte[] pick(Map<String,byte[]> files,String[] aliases,boolean image)throws IOException {
        for(String name:aliases)if(files.containsKey(name))return files.get(name);
        byte[] match=null;for(Map.Entry<String,byte[]> entry:files.entrySet()){
            String name=entry.getKey();boolean accepted=image?(name.endsWith(".png")||name.endsWith(".jpg")||name.endsWith(".jpeg")):name.endsWith(".ogg");
            if(accepted){if(match!=null)throw new IOException(image?"多个曲绘文件无法确定封面，请命名 base.jpg/png":"多个音乐文件无法确定音轨，请命名 base.ogg");match=entry.getValue();}
        }return match;
    }
    static JSONObject difficulty(JSONObject metadata,int ratingClass)throws Exception {
        JSONObject result=new JSONObject();int highest=metadata.optInt("rating",9);JSONArray list=metadata.optJSONArray("difficulties");
        if(list!=null)for(int i=0;i<list.length();i++){JSONObject d=list.getJSONObject(i);highest=Math.max(highest,d.optInt("rating",0));if(d.optInt("ratingClass",-1)==ratingClass)result=new JSONObject(d.toString());}
        result.put("ratingClass",ratingClass);
        if(result.optInt("rating",0)<=0)result.put("rating",highest);
        if(!result.has("chartDesigner"))result.put("chartDesigner",metadata.optString("chartDesigner",""));
        if(!result.has("jacketDesigner"))result.put("jacketDesigner",metadata.optString("jacketDesigner",""));
        return result;
    }
}
