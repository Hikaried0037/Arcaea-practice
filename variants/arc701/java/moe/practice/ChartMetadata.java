package moe.practice;
import android.content.res.AssetManager;
import java.io.*;
import java.util.*;
import org.json.*;

final class ChartMetadata {
    static String nonEmpty(JSONObject obj,String key,String fallback){String v=obj.optString(key,"").trim();return v.isEmpty()||v.equals("null")?fallback:v;}
    static void validateBackgrounds(JSONObject song,Set<String> backgrounds)throws Exception {
        for(String key:new String[]{"bg","bg_inverse","bgOverride"})if(song.has(key)){
            String name=song.optString(key,"").trim();
            if(name.isEmpty()||!backgrounds.contains(name))throw new IOException("JSON 的 "+key+" 背景不存在于游戏中："+name);
        }
        JSONArray diffs=song.optJSONArray("difficulties");
        if(diffs!=null)for(int i=0;i<diffs.length();i++)validateBackgrounds(diffs.getJSONObject(i),backgrounds);
    }
    static Set<String> backgrounds(AssetManager assets)throws IOException {
        Set<String> result=new HashSet<>();
        for(String name:assets.list("img/bg/1080"))if(name.endsWith(".jpg")||name.endsWith(".png"))result.add(name.substring(0,name.lastIndexOf('.')));
        return result;
    }
    static Set<String> backgrounds(File directory)throws IOException {
        Set<String> result=new HashSet<>();String[] names=directory.list();
        if(names==null)throw new IOException("无法读取外置背景目录："+directory);
        for(String name:names)if(name.endsWith(".jpg")||name.endsWith(".png"))result.add(name.substring(0,name.lastIndexOf('.')));
        return result;
    }
    static void credits(JSONObject song,JSONObject difficulty)throws Exception {
        song.put("artist",nonEmpty(song,"artist",""));
        difficulty.put("artist",nonEmpty(difficulty,"artist",song.getString("artist")));
        difficulty.put("chartDesigner",nonEmpty(difficulty,"chartDesigner",nonEmpty(song,"chartDesigner","")));
        difficulty.put("jacketDesigner",nonEmpty(difficulty,"jacketDesigner",nonEmpty(song,"jacketDesigner","")));
    }
}
